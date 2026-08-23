"""
Audit Electric Barometer sibling checkouts for dependency, metadata, and tooling consistency.

Validates declared runtime dependencies against src/ and scripts/ imports, identical
requires-python floors, tooling/ symlinks into eb-integration, pytest -m ecosystem
smoke on local trees, and each sibling's ``tooling/check.py`` on explicit ecosystem
passes (``--require-siblings``).
"""

from __future__ import annotations

import argparse
import ast
from collections.abc import Callable, Sequence
from dataclasses import dataclass
import os
from pathlib import Path
import re
import subprocess
import sys
import tomllib
from typing import Any

SIBLING_REPO_NAMES: tuple[str, ...] = (
    "eb-contracts",
    "eb-metrics",
    "eb-evaluation",
    "eb-features",
    "eb-optimization",
    "eb-adapters",
    "eb-examples",
    "electric-barometer",
)

EXPECTED_TOOLING_LINK = "../eb-integration/tooling"
_PYTEST_NO_TESTS_COLLECTED = 5
_REQ_VERSION_SPLIT = re.compile(r"\s*(?:===|==|!=|<=|>=|~=|<|>)")


@dataclass(frozen=True)
class Issue:
    repo: str
    kind: str
    message: str

    def format(self) -> str:
        return f"[{self.kind}] {self.repo}: {self.message}"


def integration_root_from_tooling(tooling_dir: Path | None = None) -> Path:
    """Return the eb-integration repo root from this script's location."""
    base = tooling_dir if tooling_dir is not None else Path(__file__).resolve().parent
    return base.resolve().parent


def ecosystem_root_from_tooling(tooling_dir: Path | None = None) -> Path:
    """Return the parent directory that holds sibling Electric Barometer checkouts."""
    return integration_root_from_tooling(tooling_dir).parent


def sibling_checkouts_present(tooling_dir: Path | None = None) -> bool:
    """Return True if at least one named sibling checkout exists next to eb-integration."""
    root = ecosystem_root_from_tooling(tooling_dir)
    return any((root / name).is_dir() for name in SIBLING_REPO_NAMES)


def discover_sibling_repos(ecosystem_root: Path) -> list[Path]:
    """Return present sibling checkouts that look like Python packages."""
    found: list[Path] = []
    for name in SIBLING_REPO_NAMES:
        path = ecosystem_root / name
        if path.is_dir() and (path / "pyproject.toml").is_file():
            found.append(path)
    return found


def canonicalize_name(name: str) -> str:
    """Normalize a distribution or import name per PEP 503."""
    return re.sub(r"[-_.]+", "-", name).strip().lower()


def requirement_distribution_name(requirement: str) -> str | None:
    """
    Extract the canonical distribution name from a PEP 508 requirement string.

    Comments and blank entries return None.
    """
    stripped = requirement.strip()
    if not stripped or stripped.startswith("#"):
        return None
    stripped = stripped.split(";", 1)[0].strip()
    if "@" in stripped:
        stripped = stripped.split("@", 1)[0].strip()
    stripped = stripped.split("[", 1)[0].strip()
    name = _REQ_VERSION_SPLIT.split(stripped, maxsplit=1)[0].strip()
    if not name:
        return None
    return canonicalize_name(name)


def is_ecosystem_import(top_level: str) -> bool:
    """Return True for ``eb_*`` or ``electric_barometer`` top-level import names."""
    return top_level == "electric_barometer" or top_level.startswith("eb_")


def load_pyproject(repo: Path) -> dict[str, Any]:
    """Load a repository pyproject.toml as a dict."""
    path = repo / "pyproject.toml"
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    if not isinstance(data, dict):
        raise TypeError(f"{path} did not parse as a TOML table")
    return data


def project_name(data: dict[str, Any]) -> str | None:
    """Return the canonical [project].name, or None if missing."""
    raw = data.get("project", {}).get("name")
    if not isinstance(raw, str) or not raw.strip():
        return None
    return canonicalize_name(raw)


def declared_runtime_dependencies(data: dict[str, Any]) -> set[str]:
    """Return canonical names from [project].dependencies (runtime only)."""
    raw = data.get("project", {}).get("dependencies", [])
    if raw is None:
        return set()
    if not isinstance(raw, list):
        raise TypeError("project.dependencies must be an array of strings")
    names: set[str] = set()
    for item in raw:
        if not isinstance(item, str):
            continue
        parsed = requirement_distribution_name(item)
        if parsed is not None:
            names.add(parsed)
    return names


def requires_python(data: dict[str, Any]) -> str | None:
    """Return the [project].requires-python string, or None if absent."""
    raw = data.get("project", {}).get("requires-python")
    if not isinstance(raw, str) or not raw.strip():
        return None
    return raw.strip()


def ecosystem_imports_in_source(path: Path) -> set[str]:
    """
    Return top-level ecosystem import names referenced by a Python file.

    Relative imports (``from .foo import ...``) are ignored. Imports nested
    under ``try`` are treated as optional and are not required in
    ``project.dependencies``.
    """
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    found: set[str] = set()
    _collect_ecosystem_imports(tree, found, in_try=False)
    return found


def _record_imported_name(name: str, found: set[str]) -> None:
    top = name.split(".")[0]
    if is_ecosystem_import(top):
        found.add(top)


def _collect_ecosystem_imports(node: ast.AST, found: set[str], *, in_try: bool) -> None:
    nested_try = in_try or isinstance(node, ast.Try)
    if not nested_try:
        if isinstance(node, ast.Import):
            for alias in node.names:
                _record_imported_name(alias.name, found)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            _record_imported_name(node.module, found)
    for child in ast.iter_child_nodes(node):
        _collect_ecosystem_imports(child, found, in_try=nested_try)


def iter_src_python_files(repo: Path) -> list[Path]:
    """Return Python files under src/, if that directory exists."""
    src = repo / "src"
    if not src.is_dir():
        return []
    return sorted(p for p in src.rglob("*.py") if p.is_file())


def iter_scripts_python_files(repo: Path) -> list[Path]:
    """Return Python files under scripts/, if that directory exists."""
    scripts = repo / "scripts"
    if not scripts.is_dir():
        return []
    return sorted(p for p in scripts.rglob("*.py") if p.is_file())


def iter_audit_python_files(repo: Path) -> list[Path]:
    """Return Python files whose ecosystem imports must be declared as dependencies."""
    return sorted({*iter_src_python_files(repo), *iter_scripts_python_files(repo)})


def normalize_link_target(raw: str) -> str:
    """Normalize a symlink target to POSIX form without a trailing slash."""
    return raw.replace("\\", "/").rstrip("/")


def tooling_symlink_issues(repo: Path, integration_tooling: Path) -> list[Issue]:
    """Return issues if ``repo/tooling`` is not a valid symlink into eb-integration."""
    tooling = repo / "tooling"
    name = repo.name
    if not tooling.exists() and not tooling.is_symlink():
        return [
            Issue(name, "symlink", f"missing tooling symlink (expected {EXPECTED_TOOLING_LINK})")
        ]
    if not tooling.is_symlink():
        return [Issue(name, "symlink", "tooling exists but is not a symlink")]

    raw_target = normalize_link_target(str(tooling.readlink()))
    if raw_target != EXPECTED_TOOLING_LINK:
        return [
            Issue(
                name,
                "symlink",
                f"tooling symlink target is {raw_target!r}, expected {EXPECTED_TOOLING_LINK!r}",
            )
        ]

    try:
        resolved = tooling.resolve(strict=True)
    except OSError:
        return [Issue(name, "symlink", "tooling symlink is broken")]

    expected = integration_tooling.resolve()
    if resolved != expected:
        return [
            Issue(
                name,
                "symlink",
                f"tooling symlink resolves to {resolved}, expected {expected}",
            )
        ]
    return []


def defines_ecosystem_marker(data: dict[str, Any]) -> bool:
    """Return True if pyproject.toml declares a pytest marker named ecosystem."""
    markers = data.get("tool", {}).get("pytest", {}).get("ini_options", {}).get("markers", [])
    if isinstance(markers, str):
        markers = [markers]
    if not isinstance(markers, list):
        return False
    for marker in markers:
        if not isinstance(marker, str):
            continue
        if marker.split(":", 1)[0].strip() == "ecosystem":
            return True
    return False


def local_src_pythonpath(repos: Sequence[Path]) -> str:
    """Build a PYTHONPATH that prefers each checkout's src/ tree."""
    parts = [str((repo / "src").resolve()) for repo in repos if (repo / "src").is_dir()]
    existing = os.environ.get("PYTHONPATH", "")
    if existing:
        parts.append(existing)
    return os.pathsep.join(parts)


def _print_proc(proc: subprocess.CompletedProcess[str]) -> None:
    if proc.stdout:
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
    if proc.stderr:
        print(proc.stderr, end="" if proc.stderr.endswith("\n") else "\n", file=sys.stderr)


def invoke_ecosystem_pytest(*, cwd: Path, pythonpath: str) -> int:
    """Run ``pytest -m ecosystem`` in ``cwd`` with local source trees on PYTHONPATH."""
    env = os.environ.copy()
    env["PYTHONPATH"] = pythonpath
    cmd = [sys.executable, "-m", "pytest", "-m", "ecosystem", "-q", "--tb=short"]
    print(f"\n$ {' '.join(cmd)}  (cwd={cwd.name})")
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    _print_proc(proc)
    return int(proc.returncode)


def leaf_check_script(repo: Path) -> Path:
    """Return the expected ``tooling/check.py`` path for a sibling checkout."""
    return repo / "tooling" / "check.py"


def invoke_leaf_check(*, cwd: Path) -> int:
    """Run a sibling's ``tooling/check.py --skip-ecosystem``."""
    script = leaf_check_script(cwd)
    cmd = [sys.executable, str(script), "--skip-ecosystem"]
    print(f"\n$ {' '.join(cmd)}  (cwd={cwd.name})")
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        env=os.environ.copy(),
        check=False,
    )
    _print_proc(proc)
    return int(proc.returncode)


def _missing_named_siblings(ecosystem_root: Path) -> list[str]:
    """Return sibling names that are absent or lack pyproject.toml."""
    present = {repo.name for repo in discover_sibling_repos(ecosystem_root)}
    return [name for name in SIBLING_REPO_NAMES if name not in present]


def _audit_leaf_checks(
    siblings: Sequence[Path],
    *,
    runner: Callable[..., int],
) -> list[Issue]:
    """Invoke or fail closed on each sibling's local ``tooling/check.py``."""
    issues: list[Issue] = []
    for repo in siblings:
        script = leaf_check_script(repo)
        if not script.is_file():
            issues.append(
                Issue(
                    repo.name,
                    "leaf-check",
                    "missing tooling/check.py; cannot verify local check coverage",
                )
            )
            continue
        print(f"\nLeaf check: {repo.name}")
        rc = runner(cwd=repo)
        if rc != 0:
            issues.append(
                Issue(
                    repo.name,
                    "leaf-check",
                    f"tooling/check.py --skip-ecosystem failed with exit code {rc}",
                )
            )
    return issues


def _audit_dependencies(repo: Path, data: dict[str, Any]) -> list[Issue]:
    name = repo.name
    proj = project_name(data)
    if proj is None:
        return [Issue(name, "metadata", "missing project.name")]

    try:
        declared = declared_runtime_dependencies(data)
    except TypeError as exc:
        return [Issue(name, "metadata", str(exc))]

    issues: list[Issue] = []
    for path in iter_audit_python_files(repo):
        try:
            imported = ecosystem_imports_in_source(path)
        except SyntaxError as exc:
            rel = path.relative_to(repo).as_posix()
            issues.append(Issue(name, "parse", f"{rel}: syntax error: {exc.msg}"))
            continue
        for top in sorted(imported):
            dist = canonicalize_name(top)
            if dist == proj:
                continue
            if dist not in declared:
                rel = path.relative_to(repo).as_posix()
                issues.append(
                    Issue(
                        name,
                        "dependency",
                        f"{rel} imports {top} but {dist} is not declared in project.dependencies",
                    )
                )
    return issues


def _audit_python_floor(repos: Sequence[tuple[Path, dict[str, Any]]]) -> list[Issue]:
    floors: dict[str, str] = {}
    issues: list[Issue] = []
    for repo, data in repos:
        floor = requires_python(data)
        if floor is None:
            issues.append(Issue(repo.name, "python-floor", "missing project.requires-python"))
            continue
        floors[repo.name] = floor

    unique = set(floors.values())
    if len(unique) > 1:
        detail = ", ".join(f"{repo}={value!r}" for repo, value in sorted(floors.items()))
        issues.append(
            Issue(
                "*",
                "python-floor",
                f"requires-python is not identical across checkouts: {detail}",
            )
        )
    return issues


def run_audit(
    *,
    ecosystem_root: Path,
    integration_root: Path,
    require_siblings: bool = False,
    run_pytest: bool = True,
    run_leaf_checks: bool = False,
    pytest_runner: Callable[..., int] | None = None,
    leaf_check_runner: Callable[..., int] | None = None,
) -> int:
    """
    Run the ecosystem consistency audit.

    Returns 0 on success, 1 when issues are found, and 2 when required siblings are missing.
    """
    siblings = discover_sibling_repos(ecosystem_root)
    print(f"Ecosystem root: {ecosystem_root}")
    print(f"Integration:    {integration_root}")
    if siblings:
        print(f"Siblings:       {', '.join(repo.name for repo in siblings)}")
    else:
        print("Siblings:       (none)")

    missing_named = _missing_named_siblings(ecosystem_root)
    if missing_named:
        print(f"Missing:        {', '.join(missing_named)}")

    if not siblings:
        message = f"No sibling repositories found under {ecosystem_root}."
        if require_siblings:
            print(f"ERROR: {message}", file=sys.stderr)
            return 2
        print(f"NOTE: {message} Skipping ecosystem audit.")
        return 0

    issues: list[Issue] = []
    if require_siblings and missing_named:
        issues.append(
            Issue(
                "*",
                "siblings",
                "missing sibling checkouts required for a full ecosystem pass: "
                + ", ".join(missing_named),
            )
        )

    loaded: list[tuple[Path, dict[str, Any]]] = []
    for repo in siblings:
        try:
            data = load_pyproject(repo)
        except (OSError, tomllib.TOMLDecodeError, TypeError) as exc:
            issues.append(Issue(repo.name, "metadata", f"cannot read pyproject.toml: {exc}"))
            continue
        loaded.append((repo, data))

    integration_data: dict[str, Any] | None = None
    if (integration_root / "pyproject.toml").is_file():
        try:
            integration_data = load_pyproject(integration_root)
            loaded.append((integration_root, integration_data))
        except (OSError, tomllib.TOMLDecodeError, TypeError) as exc:
            issues.append(
                Issue(
                    integration_root.name,
                    "metadata",
                    f"cannot read pyproject.toml: {exc}",
                )
            )

    integration_resolved = integration_root.resolve()
    for repo, data in loaded:
        if repo.resolve() == integration_resolved:
            continue
        issues.extend(_audit_dependencies(repo, data))

    issues.extend(_audit_python_floor(loaded))

    integration_tooling = (integration_root / "tooling").resolve()
    for repo, _data in loaded:
        if repo.resolve() == integration_root.resolve():
            continue
        issues.extend(tooling_symlink_issues(repo, integration_tooling))

    pytest_issues: list[Issue] = []
    if run_pytest:
        runner = pytest_runner if pytest_runner is not None else invoke_ecosystem_pytest
        pythonpath = local_src_pythonpath([repo for repo, _data in loaded])
        pytest_targets: list[Path] = []
        skipped: list[str] = []
        for repo, data in loaded:
            if defines_ecosystem_marker(data) and (repo / "tests").is_dir():
                pytest_targets.append(repo)
            else:
                skipped.append(repo.name)
        if skipped:
            print("Skipping pytest -m ecosystem in trees without the marker: " + ", ".join(skipped))
        if not pytest_targets:
            pytest_issues.append(
                Issue("*", "pytest", "no local source tree declares a pytest ecosystem marker")
            )
        for target in pytest_targets:
            rc = runner(cwd=target, pythonpath=pythonpath)
            if rc == 0:
                continue
            if rc == _PYTEST_NO_TESTS_COLLECTED:
                print(f"NOTE: no tests collected for marker 'ecosystem' in {target.name}")
                continue
            pytest_issues.append(
                Issue(target.name, "pytest", f"pytest -m ecosystem failed with exit code {rc}")
            )

    leaf_issues: list[Issue] = []
    if run_leaf_checks:
        runner = leaf_check_runner if leaf_check_runner is not None else invoke_leaf_check
        leaf_issues = _audit_leaf_checks(siblings, runner=runner)

    all_issues = [*issues, *pytest_issues, *leaf_issues]
    if all_issues:
        print("\nEcosystem audit failed:")
        for issue in all_issues:
            print(f"  - {issue.format()}", file=sys.stderr)
        return 1

    print("\nEcosystem audit passed.")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit sibling Electric Barometer checkouts for cross-repo consistency.",
    )
    parser.add_argument(
        "--require-siblings",
        action="store_true",
        help="Fail if any named sibling checkout is missing next to eb-integration.",
    )
    parser.add_argument(
        "--skip-pytest",
        action="store_true",
        help="Skip pytest -m ecosystem smoke (metadata and symlink checks still run).",
    )
    parser.add_argument(
        "--skip-leaf-checks",
        action="store_true",
        help="Skip sibling tooling/check.py coverage (metadata and symlink checks still run).",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    tooling_dir = Path(__file__).resolve().parent
    return run_audit(
        ecosystem_root=ecosystem_root_from_tooling(tooling_dir),
        integration_root=integration_root_from_tooling(tooling_dir),
        require_siblings=args.require_siblings,
        run_pytest=not args.skip_pytest,
        run_leaf_checks=args.require_siblings and not args.skip_leaf_checks,
    )


if __name__ == "__main__":
    raise SystemExit(main())
