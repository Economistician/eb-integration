"""
EB local validation runner.

This script is intended to provide a single command that performs a full local validation
pass with CI parity across the Electric Barometer ecosystem.

Default behavior:
- Check formatting; if needed, apply formatting.
- Check lint; if needed, apply safe fixes.
- Re-check formatting and lint after fixes.
- Run Pyright type checking (restricted to src/ and tests/; auto-skip if none exist).
- Run pre-commit over all files (re-run once if hooks made changes).
- Run pytest.

Run from repo root:
    python tooling/check.py

Options:
    python tooling/check.py --no-fix
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import configparser
import os
from pathlib import Path
import subprocess
import sys


def _find_repo_root(start: Path) -> Path:
    """Find repo root by walking up until pyproject.toml is found."""
    for p in (start, *start.parents):
        if (p / "pyproject.toml").is_file():
            return p
    # Fallback to CWD if not found (still usable for many repos)
    return start


def _run(cmd: Sequence[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    print(f"\n$ {' '.join(cmd)}")
    return subprocess.run(
        list(cmd),
        cwd=str(cwd),
        text=True,
        capture_output=True,
        env=os.environ.copy(),
    )


def _print_proc(proc: subprocess.CompletedProcess[str]) -> None:
    if proc.stdout:
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
    if proc.stderr:
        print(proc.stderr, end="" if proc.stderr.endswith("\n") else "\n", file=sys.stderr)


def _require_ok(proc: subprocess.CompletedProcess[str], *, step: str) -> None:
    _print_proc(proc)
    if proc.returncode != 0:
        raise RuntimeError(f"{step} failed with exit code {proc.returncode}.")


def _submodule_paths(repo_root: Path) -> list[Path]:
    """
    Return submodule paths listed in .gitmodules as repo-root-relative Paths.

    We intentionally exclude submodules from all validation steps; the runner is meant to
    validate the repo you're in, not the repos it happens to vendor via submodules.
    """
    gm = repo_root / ".gitmodules"
    if not gm.is_file():
        return []

    cp = configparser.ConfigParser()
    cp.read(gm)

    paths: list[Path] = []
    for section in cp.sections():
        if cp.has_option(section, "path"):
            raw = cp.get(section, "path").strip()
            if raw:
                # Normalize slashes; keep as Path relative to repo_root.
                paths.append(Path(raw.replace("\\", "/")).resolve())

    # De-dupe (by string form) but keep stable ordering
    unique: dict[str, Path] = {}
    for p in paths:
        unique.setdefault(str(p), p)
    return list(unique.values())


def _relative_submodule_paths(repo_root: Path) -> list[str]:
    """
    Return submodule paths as repo-root-relative POSIX strings for tool CLI excludes/ignores.
    """
    rels: list[str] = []
    for p in _submodule_paths(repo_root):
        try:
            rel = p.relative_to(repo_root.resolve())
        except ValueError:
            # If something odd happens (shouldn't), ignore that entry.
            continue
        rels.append(rel.as_posix().rstrip("/"))
    return sorted(set(rels))


def _ruff_exclude_args(repo_root: Path) -> list[str]:
    """
    Build Ruff CLI exclude arguments including any detected submodules.

    Returns: ["--exclude", "submod/a", "--exclude", "vendor/b", ...]
    """
    excludes = _relative_submodule_paths(repo_root)
    args: list[str] = []
    for p in excludes:
        args.extend(["--exclude", p])
    return args


def _pytest_ignore_args(repo_root: Path) -> list[str]:
    """
    Build pytest ignore arguments for detected submodules.

    Returns: ["--ignore=path1", "--ignore=path2", ...]
    """
    return [f"--ignore={p}" for p in _relative_submodule_paths(repo_root)]


def _is_under_any(path: Path, roots: Sequence[Path]) -> bool:
    """Return True if path is inside any of the provided root directories."""
    for r in roots:
        try:
            path.resolve().relative_to(r.resolve())
        except ValueError:
            continue
        else:
            return True
    return False


def _has_python_files(repo_root: Path, *, excluded_roots: Sequence[Path]) -> bool:
    """
    Return True if repo contains any Python files (excluding common vendor/build dirs and submodules).

    This is used only as a guard for whether pyright is worth running.
    """
    skip_dirs = {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        "env",
        "__pycache__",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        "build",
        "dist",
        "site",
        ".tox",
        "node_modules",
    }

    for p in repo_root.rglob("*.py"):
        parts = set(p.parts)
        if parts & skip_dirs:
            continue
        if _is_under_any(p, excluded_roots):
            continue
        return True
    return False


def _pyright_targets(repo_root: Path) -> list[str]:
    """
    Return the Pyright scan targets.

    We intentionally restrict to the real code surface area for speed:
    - src/
    - tests/

    Only include targets that actually exist in the repo.
    """
    candidates = [repo_root / "src", repo_root / "tests"]
    return [str(p.relative_to(repo_root)) for p in candidates if p.exists()]


def main() -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument(
        "--no-fix",
        action="store_true",
        help="Only run checks; do not apply any automatic fixes/formatting.",
    )
    parser.add_argument(
        "--skip-precommit",
        action="store_true",
        help="Skip pre-commit (useful if you don't have it installed locally).",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip pytest.",
    )
    args = parser.parse_args()

    repo_root = _find_repo_root(Path.cwd())
    tooling_dir = Path(__file__).resolve().parent

    ruff_config = tooling_dir / "ruff.toml"
    pyright_config = tooling_dir / "pyrightconfig.json"
    precommit_config = tooling_dir / ".pre-commit-config.yaml"

    if not ruff_config.is_file():
        print(f"ERROR: Ruff config not found at: {ruff_config}", file=sys.stderr)
        return 2
    if not pyright_config.is_file():
        print(f"ERROR: Pyright config not found at: {pyright_config}", file=sys.stderr)
        return 2

    fix_enabled = not args.no_fix

    submodule_rel_paths = _relative_submodule_paths(repo_root)
    submodule_roots = [repo_root / p for p in submodule_rel_paths]
    ruff_excludes = _ruff_exclude_args(repo_root)
    pytest_ignores = _pytest_ignore_args(repo_root)

    print(f"Repo root:   {repo_root}")
    print(f"Tooling dir: {tooling_dir}")
    print(f"Fix enabled: {fix_enabled}")
    if submodule_rel_paths:
        print(f"Submodules:  {', '.join(submodule_rel_paths)}")
    else:
        print("Submodules:  (none)")

    try:
        # -------------------------
        # Ruff format (check, then fix if needed)
        # -------------------------
        proc = _run(
            ["ruff", "format", "--check", ".", "--config", str(ruff_config), *ruff_excludes],
            cwd=repo_root,
        )
        if proc.returncode != 0:
            if not fix_enabled:
                _require_ok(proc, step="ruff format --check")
            print("\nFormatting needed; applying ruff format ...")
            _require_ok(
                _run(
                    ["ruff", "format", ".", "--config", str(ruff_config), *ruff_excludes],
                    cwd=repo_root,
                ),
                step="ruff format",
            )
            _require_ok(
                _run(
                    [
                        "ruff",
                        "format",
                        "--check",
                        ".",
                        "--config",
                        str(ruff_config),
                        *ruff_excludes,
                    ],
                    cwd=repo_root,
                ),
                step="ruff format --check (post-fix)",
            )
        else:
            _print_proc(proc)

        # -------------------------
        # Ruff lint (check, then fix if needed)
        # -------------------------
        proc = _run(
            ["ruff", "check", ".", "--config", str(ruff_config), *ruff_excludes],
            cwd=repo_root,
        )
        if proc.returncode != 0:
            if not fix_enabled:
                _require_ok(proc, step="ruff check")
            print("\nLint issues found; applying ruff check --fix ...")
            _require_ok(
                _run(
                    ["ruff", "check", ".", "--fix", "--config", str(ruff_config), *ruff_excludes],
                    cwd=repo_root,
                ),
                step="ruff check --fix",
            )
            _require_ok(
                _run(
                    ["ruff", "check", ".", "--config", str(ruff_config), *ruff_excludes],
                    cwd=repo_root,
                ),
                step="ruff check (post-fix)",
            )
        else:
            _print_proc(proc)

        # -------------------------
        # Ruff format (final check)
        # -------------------------
        _require_ok(
            _run(
                ["ruff", "format", "--check", ".", "--config", str(ruff_config), *ruff_excludes],
                cwd=repo_root,
            ),
            step="ruff format --check (final)",
        )

        # -------------------------
        # Pyright (type check) - restricted to src/ and tests/
        # -------------------------
        targets = _pyright_targets(repo_root)
        if not targets:
            # If a repo doesn't have src/ or tests/ yet, don't waste time scanning the world.
            print("\n⏭️  Skipping pyright (no src/ or tests/ directories found).")
        else:
            # Avoid invoking pyright in docs-only repos that still have empty src/tests,
            # and avoid counting any Python files that only live in submodules.
            if not _has_python_files(repo_root, excluded_roots=submodule_roots):
                print("\n⏭️  Skipping pyright (no .py files found in repo outside submodules).")
            else:
                _require_ok(
                    _run(["pyright", "-p", str(pyright_config), *targets], cwd=repo_root),
                    step=f"pyright ({', '.join(targets)})",
                )

        # -------------------------
        # Pre-commit (CI parity)
        # -------------------------
        if not args.skip_precommit:
            if not precommit_config.is_file():
                print(f"NOTE: pre-commit config not found at: {precommit_config} (skipping)")
            else:
                proc = _run(
                    [
                        sys.executable,
                        "-m",
                        "pre_commit",
                        "run",
                        "--all-files",
                        "--config",
                        str(precommit_config),
                    ],
                    cwd=repo_root,
                )
                _print_proc(proc)
                if proc.returncode != 0:
                    # Pre-commit can fail because it applied changes. Re-run once.
                    print("\nPre-commit reported failures/changes; re-running once ...")
                    _require_ok(
                        _run(
                            [
                                sys.executable,
                                "-m",
                                "pre_commit",
                                "run",
                                "--all-files",
                                "--config",
                                str(precommit_config),
                            ],
                            cwd=repo_root,
                        ),
                        step="pre-commit (second pass)",
                    )

        # -------------------------
        # Pytest
        # -------------------------
        if not args.skip_tests:
            _require_ok(_run(["pytest", *pytest_ignores], cwd=repo_root), step="pytest")

    except RuntimeError as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        return 1

    print("\n✅ All checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
