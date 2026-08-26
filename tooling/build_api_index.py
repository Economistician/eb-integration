"""
Build a generated, canonical cross-package API index for the EB ecosystem.

This script generates: llm/api_index.json

Design goals:
- Deterministic output (stable ordering, stable IDs, no wall-clock, interpreter,
  or install-environment fields)
- Only indexes public surfaces declared via package/module __all__
- Captures minimal, useful metadata for LLM-driven discovery
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from enum import Enum
import importlib
import inspect
import json
from pathlib import Path
import pkgutil
import re
import sys
from types import ModuleType
from typing import Any

RE_WS = re.compile(r"\s+")

REPO_INDEX_REL = Path("llm") / "repo_index.json"


DEFAULT_PACKAGES: list[str] = [
    # Fallback only. Prefer deriving packages from llm/repo_index.json.
    "eb_contracts",
    "eb_metrics",
    "eb_evaluation",
    "electric_barometer",
    "eb_optimization",
    "eb_features",
    "eb_adapters",
]


@dataclass(frozen=True)
class ApiEntry:
    id: str
    package: str
    module: str
    name: str
    kind: str  # "function" | "class"
    import_path: str
    public_import: str
    signature: str | None
    doc_summary: str | None
    tags: list[str]
    io: dict[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "package": self.package,
            "module": self.module,
            "name": self.name,
            "kind": self.kind,
            "import_path": self.import_path,
            "public_import": self.public_import,
            "signature": self.signature,
            "doc_summary": self.doc_summary,
            "tags": self.tags,
            "io": self.io,
        }


def _repo_root() -> Path:
    # tooling/build_api_index.py -> repo root
    return Path(__file__).resolve().parents[1]


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _packages_from_repo_index(root: Path) -> tuple[list[str], dict[str, str] | None]:
    """
    Derive package import roots from llm/repo_index.json.

    Returns (packages, diagnostics). Diagnostics are non-fatal and intended
    for human troubleshooting.
    """
    path = root / REPO_INDEX_REL
    if not path.exists():
        return ([], {str(REPO_INDEX_REL): "FileNotFoundError: repo_index.json not found"})

    try:
        payload = _read_json(path)
    except Exception as e:
        return ([], {str(REPO_INDEX_REL): f"{type(e).__name__}: {e}"})

    repos = payload.get("repos", [])
    if not isinstance(repos, list):
        return ([], {str(REPO_INDEX_REL): "ValueError: repos must be a list"})

    pkgs: set[str] = set()
    diag: dict[str, str] = {}

    for repo in repos:
        if not isinstance(repo, dict):
            continue
        packages = repo.get("packages", [])
        if not isinstance(packages, list):
            continue

        for p in packages:
            if not isinstance(p, dict):
                continue
            if p.get("index_in_api_catalog", True) is False:
                continue
            import_root = p.get("import_root")
            if isinstance(import_root, str) and import_root.strip():
                pkgs.add(import_root.strip())

    out = sorted(pkgs)
    return (out, diag or None)


def _first_paragraph(doc: str | None) -> str | None:
    if not doc:
        return None
    # Normalize whitespace and take the first "paragraph" (split on blank line).
    doc = doc.strip()
    if not doc:
        return None
    parts = re.split(r"\n\s*\n", doc, maxsplit=1)
    first = RE_WS.sub(" ", parts[0]).strip()
    return first or None


def _safe_signature(obj: Any) -> str | None:
    try:
        return str(inspect.signature(obj))
    except (TypeError, ValueError):
        return None


def _is_enum_class(obj: Any) -> bool:
    return inspect.isclass(obj) and issubclass(obj, Enum)


def _is_builtin_origin(obj: Any) -> bool:
    return getattr(obj, "__module__", None) == "builtins"


def _entry_signature(obj: Any) -> str | None:
    # Enum constructors and builtin types leak interpreter-specific inspect text
    # (Python 3.11 vs 3.13+ Enum.__call__, float.__doc__, etc.).
    if _is_enum_class(obj) or _is_builtin_origin(obj):
        return None
    return _safe_signature(obj)


def _entry_doc_summary(obj: Any) -> str | None:
    if _is_builtin_origin(obj):
        return None
    return _first_paragraph(getattr(obj, "__doc__", None))


def _kind(obj: Any) -> str | None:
    if inspect.isclass(obj):
        return "class"
    if inspect.isfunction(obj) or inspect.isbuiltin(obj) or inspect.ismethod(obj):
        return "function"
    # Treat callables that are not classes/functions as unsupported for indexing (for now).
    return None


def _make_tags(package: str, module: str, name: str, doc_summary: str | None) -> list[str]:
    # Very light heuristics; workflows.yml will be the real “canonical routing”.
    blob = " ".join([package, module, name, doc_summary or ""]).lower()
    tags: set[str] = set()

    for t in [
        "workflow",
        "governance",
        "evaluation",
        "validate",
        "validation",
        "contract",
        "panel",
        "hierarchy",
        "ral",
        "metric",
        "optimiz",
        "forecast",
        "adapter",
        "dataframe",
        "df",
    ]:
        if t in blob:
            # normalize common variants
            if t == "optimiz":
                tags.add("optimization")
            elif t in {"validate", "validation"}:
                tags.add("validation")
            elif t in {"dataframe", "df"}:
                tags.add("dataframe")
            else:
                tags.add(t)

    # Package-level anchors are useful for search
    tags.add(package)
    return sorted(tags)


def _public_symbols(mod: ModuleType) -> list[str]:
    exports = getattr(mod, "__all__", None)
    if exports is None:
        return []
    if not isinstance(exports, list | tuple):
        return []
    out: list[str] = []
    for x in exports:
        if isinstance(x, str) and x:
            out.append(x)
    return out


def _iter_submodules(pkg: ModuleType) -> Iterator[str]:
    """
    Yield fully-qualified module names beneath a package.

    We intentionally do NOT recurse into non-package modules except via pkgutil.
    Deterministic ordering is enforced by sorting discovered names.
    """
    pkg_path = getattr(pkg, "__path__", None)
    pkg_name = getattr(pkg, "__name__", None)
    if pkg_path is None or not isinstance(pkg_name, str) or not pkg_name:
        return iter(())

    names: list[str] = []
    for m in pkgutil.walk_packages(pkg_path, prefix=pkg_name + "."):
        names.append(m.name)
    names.sort()
    return iter(names)


def _index_module_exports(package: str, mod: ModuleType, entries: list[ApiEntry]) -> None:
    """
    Index all public symbols exported by `mod.__all__` into `entries`.

    IMPORTANT: The canonical import location for an export is the module that
    exports it (i.e., `mod.__name__`), not necessarily `obj.__module__`.

    Many ecosystems re-export symbols (or provide typing aliases) where
    `obj.__module__` is misleading (e.g., "builtins"). We therefore build
    actionable imports from the exporting module and preserve `obj.__module__`
    as metadata.
    """
    names = _public_symbols(mod)
    if not names:
        return

    exporting_module = getattr(mod, "__name__", None) or package

    for name in names:
        if not hasattr(mod, name):
            continue

        obj = getattr(mod, name)
        kind = _kind(obj)
        if kind is None:
            continue

        defined_in = getattr(obj, "__module__", None)

        module = exporting_module
        import_path = f"{module}:{name}"
        public_import = f"from {module} import {name}"
        sig = _entry_signature(obj)
        doc_summary = _entry_doc_summary(obj)
        tags = _make_tags(package=package, module=module, name=name, doc_summary=doc_summary)

        entry_id = f"{package}:{module}:{name}"

        io: dict[str, Any] | None = None
        if defined_in and defined_in != module:
            # Preserve origin information without changing the top-level schema.
            io = {"defined_in": defined_in}

        entries.append(
            ApiEntry(
                id=entry_id,
                package=package,
                module=module,
                name=name,
                kind=kind,
                import_path=import_path,
                public_import=public_import,
                signature=sig,
                doc_summary=doc_summary,
                tags=tags,
                io=io,  # reserved for future: required/provided columns, contracts, etc.
            )
        )


def _index_package(package: str) -> tuple[list[ApiEntry], dict[str, str] | None]:
    """
    Returns (entries, import_errors_by_module).

    We index:
    - package root exports (package.__all__)
    - all submodule exports (submodule.__all__), for every importable submodule under the package
    """
    try:
        pkg = importlib.import_module(package)
    except Exception as e:
        return ([], {package: f"{type(e).__name__}: {e}"})

    entries: list[ApiEntry] = []
    import_errors: dict[str, str] = {}

    # Index root exports
    _index_module_exports(package=package, mod=pkg, entries=entries)

    # Index submodule exports
    for mod_name in _iter_submodules(pkg):
        try:
            mod = importlib.import_module(mod_name)
        except Exception as e:
            import_errors[mod_name] = f"{type(e).__name__}: {e}"
            continue
        _index_module_exports(package=package, mod=mod, entries=entries)

    # Deterministic unique ordering (avoid duplicates across re-exports)
    uniq: dict[tuple[str, str, str], ApiEntry] = {}
    for e in entries:
        key = (e.package, e.module, e.name)
        if key not in uniq:
            uniq[key] = e

    out = list(uniq.values())
    out.sort(key=lambda e: (e.package, e.module, e.name))

    return (out, import_errors or None)


def build_api_index(
    packages: Iterable[str],
    *,
    ecosystem_source: str | None = None,
) -> dict[str, Any]:
    all_entries: list[ApiEntry] = []
    packages_indexed: list[str] = []
    import_errors: dict[str, str] = {}

    for pkg in packages:
        pkg = pkg.strip()
        if not pkg:
            continue

        entries, errs = _index_package(pkg)
        if errs:
            # Root or submodule import failures are reported on stderr only.
            # They must not land in the committed golden file: optional packages
            # and extra extras would otherwise make CI vs local diffs.
            import_errors.update(errs)

        # Only count a package as "indexed" if its root imported successfully.
        if pkg not in import_errors:
            packages_indexed.append(pkg)

        all_entries.extend(entries)

    # Deterministic final ordering
    all_entries.sort(key=lambda e: (e.package, e.module, e.name))

    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "generator": {
            "repo": "eb-integration",
            "script": "tooling/build_api_index.py",
            "script_version": None,
        },
        "ecosystem": {
            "install_mode": "editable",
            "packages_indexed": packages_indexed,
        },
        "entries": [e.to_dict() for e in all_entries],
    }

    if ecosystem_source is not None:
        payload["ecosystem"]["package_source"] = ecosystem_source

    if import_errors:
        for mod_name, msg in sorted(import_errors.items()):
            print(f"API index skipped {mod_name}: {msg}", file=sys.stderr)

    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate llm/api_index.json from EB package/module __all__ exports."
    )
    parser.add_argument(
        "--packages",
        nargs="*",
        default=None,
        help="Override the default package list (space-separated).",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output path (default: <repo_root>/llm/api_index.json).",
    )
    args = parser.parse_args(argv)

    root = _repo_root()

    packages: list[str]
    ecosystem_source: str | None = None

    if args.packages is not None and len(args.packages) > 0:
        packages = args.packages
        ecosystem_source = "cli"
    else:
        repo_pkgs, repo_diag = _packages_from_repo_index(root)
        if repo_diag:
            for key, msg in sorted(repo_diag.items()):
                print(f"API index {key}: {msg}", file=sys.stderr)
        if repo_pkgs:
            packages = repo_pkgs
            ecosystem_source = str(REPO_INDEX_REL).replace("\\", "/")
        else:
            packages = DEFAULT_PACKAGES
            ecosystem_source = "DEFAULT_PACKAGES"

    out_path = Path(args.out) if args.out else (root / "llm" / "api_index.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    payload = build_api_index(
        packages,
        ecosystem_source=ecosystem_source,
    )

    # Deterministic JSON formatting
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"Wrote api index: {out_path}  (entries={len(payload['entries'])}, packages={len(payload['ecosystem']['packages_indexed'])})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
