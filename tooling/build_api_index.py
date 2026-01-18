"""
Build a generated, canonical cross-package API index for the EB ecosystem.

This script generates: llm/api_index.json

Design goals:
- Deterministic output (stable ordering, stable IDs)
- Only indexes public surfaces declared via package __all__
- Captures minimal, useful metadata for LLM-driven discovery
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib
import inspect
import json
import platform
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable


RE_WS = re.compile(r"\s+")


DEFAULT_PACKAGES: list[str] = [
    # Keep this aligned with what eb-integration can install in ".[ecosystem]"
    "eb_contracts",
    "eb_metrics",
    "eb_evaluation",
    "electric_barometer",
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

    for t in ["workflow", "governance", "evaluation", "validate", "validation", "contract", "panel", "hierarchy", "ral", "metric", "optimiz", "forecast", "adapter", "dataframe", "df"]:
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
    if not isinstance(exports, (list, tuple)):
        return []
    out: list[str] = []
    for x in exports:
        if isinstance(x, str) and x:
            out.append(x)
    return out


def _index_package(package: str) -> tuple[list[ApiEntry], str | None]:
    """
    Returns (entries, import_error_message).
    """
    try:
        pkg = importlib.import_module(package)
    except Exception as e:  # noqa: BLE001 - we want the error string for reporting
        return ([], f"{type(e).__name__}: {e}")

    names = _public_symbols(pkg)
    if not names:
        # No __all__ => nothing public is indexed for this package.
        return ([], None)

    entries: list[ApiEntry] = []

    for name in names:
        if not hasattr(pkg, name):
            continue

        obj = getattr(pkg, name)
        kind = _kind(obj)
        if kind is None:
            continue

        module = getattr(obj, "__module__", None) or package
        import_path = f"{module}:{name}"
        public_import = f"from {module} import {name}"
        sig = _safe_signature(obj)
        doc_summary = _first_paragraph(getattr(obj, "__doc__", None))
        tags = _make_tags(package=package, module=module, name=name, doc_summary=doc_summary)

        entry_id = f"{package}:{module}:{name}"

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
                io=None,  # reserved for future: required/provided columns, contracts, etc.
            )
        )

    # Deterministic ordering
    entries.sort(key=lambda e: (e.package, e.module, e.name))
    return (entries, None)


def build_api_index(packages: Iterable[str]) -> dict[str, Any]:
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)

    all_entries: list[ApiEntry] = []
    packages_indexed: list[str] = []
    import_errors: dict[str, str] = {}

    for pkg in packages:
        pkg = pkg.strip()
        if not pkg:
            continue
        entries, err = _index_package(pkg)
        if err:
            import_errors[pkg] = err
            continue
        packages_indexed.append(pkg)
        all_entries.extend(entries)

    # Deterministic final ordering
    all_entries.sort(key=lambda e: (e.package, e.module, e.name))

    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "generated_at_utc": now.isoformat(),
        "generator": {
            "repo": "eb-integration",
            "script": "tooling/build_api_index.py",
            "script_version": None,
        },
        "ecosystem": {
            "python_version": platform.python_version(),
            "install_mode": "editable",
            "packages_indexed": packages_indexed,
        },
        "entries": [e.to_dict() for e in all_entries],
    }

    # Helpful diagnostics (non-breaking) for humans/CI logs
    if import_errors:
        payload["diagnostics"] = {"import_errors": import_errors}

    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate llm/api_index.json from EB package __all__ exports.")
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

    packages = args.packages if args.packages is not None and len(args.packages) > 0 else DEFAULT_PACKAGES

    out_path = Path(args.out) if args.out else (_repo_root() / "llm" / "api_index.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    payload = build_api_index(packages)

    # Deterministic JSON formatting
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote api index: {out_path}  (entries={len(payload['entries'])}, packages={len(payload['ecosystem']['packages_indexed'])})")
    if "diagnostics" in payload:
        print("Diagnostics present (import errors).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
