"""
Print the public API entrypoints + indexed signatures referenced by a workflow.

This is a lightweight “workflow view” helper for live exercises:
- Reads llm/workflows.yml
- Extracts the block for a given workflow id (no YAML dependency required)
- Finds referenced imports of the form: import: "from <module> import <name>"
- Looks up each (<module>, <name>) in llm/api_index.json
- Prints a deterministic, copy/paste-friendly summary

Usage:
  python tooling/llm_print_workflow.py --workflow governance_workflow_v1
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys
from typing import Any

_RE_WORKFLOW_ID = re.compile(r"^\s*-\s+id:\s*([A-Za-z0-9_]+)\s*$")
_RE_IMPORT_LINE = re.compile(r"^\s*import:\s*(?P<q>['\"])?(?P<stmt>from\s+.+?)(?P=q)?\s*$")
_RE_FROM_IMPORT = re.compile(r"^from\s+([A-Za-z0-9_.]+)\s+import\s+([A-Za-z0-9_]+)\s*$")


@dataclass(frozen=True)
class ImportRef:
    module: str
    name: str

    @property
    def import_stmt(self) -> str:
        return f"from {self.module} import {self.name}"

    @property
    def import_path(self) -> str:
        return f"{self.module}:{self.name}"


def _repo_root() -> Path:
    # tooling/llm_print_workflow.py -> repo root
    return Path(__file__).resolve().parents[1]


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {path}") from None


def _extract_workflow_block(text: str, workflow_id: str) -> str:
    """
    Extract the YAML-ish text block for the workflow with id == workflow_id.

    This is intentionally line-based to avoid adding a YAML dependency.
    It assumes workflows are declared as list items with lines like:
      - id: some_workflow_v1
    """
    lines = text.splitlines()
    start_idx: int | None = None

    for i, line in enumerate(lines):
        m = _RE_WORKFLOW_ID.match(line)
        if m and m.group(1) == workflow_id:
            start_idx = i
            break

    if start_idx is None:
        raise ValueError(f"Workflow id not found in workflows file: {workflow_id!r}")

    # Capture until the next "- id:" at the same or less indentation level.
    # We treat any subsequent workflow item as a terminator.
    end_idx = len(lines)
    for j in range(start_idx + 1, len(lines)):
        if _RE_WORKFLOW_ID.match(lines[j]):
            end_idx = j
            break

    return "\n".join(lines[start_idx:end_idx]).strip() + "\n"


def _extract_import_refs(block: str) -> list[ImportRef]:
    refs: list[ImportRef] = []
    for line in block.splitlines():
        m = _RE_IMPORT_LINE.match(line)
        if not m:
            continue

        stmt = m.group("stmt").strip()
        m2 = _RE_FROM_IMPORT.match(stmt)
        if not m2:
            # Ignore any import lines that do not follow the expected format.
            continue

        refs.append(ImportRef(module=m2.group(1), name=m2.group(2)))

    # Deterministic unique ordering
    uniq = {(r.module, r.name): r for r in refs}
    out = sorted(uniq.values(), key=lambda r: (r.module, r.name))
    return out


def _load_api_index(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"api_index.json not found: {path}") from None
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in api_index.json: {path} ({e})") from None


def _index_entries_by_import_path(api_index: dict[str, Any]) -> dict[str, dict[str, Any]]:
    entries = api_index.get("entries")
    if not isinstance(entries, list):
        return {}

    out: dict[str, dict[str, Any]] = {}
    for e in entries:
        if not isinstance(e, dict):
            continue
        import_path = e.get("import_path")
        if isinstance(import_path, str) and import_path:
            out[import_path] = e
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Print the entrypoints and indexed signatures referenced by a workflow."
    )
    parser.add_argument(
        "--workflow",
        required=True,
        help="Workflow id from llm/workflows.yml (e.g., governance_workflow_v1).",
    )
    parser.add_argument(
        "--workflows-path",
        default=None,
        help="Path to workflows file (default: <repo_root>/llm/workflows.yml).",
    )
    parser.add_argument(
        "--api-index-path",
        default=None,
        help="Path to api index JSON (default: <repo_root>/llm/api_index.json).",
    )
    args = parser.parse_args(argv)

    repo_root = _repo_root()
    workflows_path = (
        Path(args.workflows_path) if args.workflows_path else (repo_root / "llm" / "workflows.yml")
    )
    api_index_path = (
        Path(args.api_index_path) if args.api_index_path else (repo_root / "llm" / "api_index.json")
    )

    workflows_text = _read_text(workflows_path)
    block = _extract_workflow_block(workflows_text, args.workflow)
    refs = _extract_import_refs(block)

    api_index = _load_api_index(api_index_path)
    by_import_path = _index_entries_by_import_path(api_index)

    print(f"Workflow: {args.workflow}")
    print(f"Workflows file: {workflows_path}")
    print(f"API index: {api_index_path}")
    print()

    if not refs:
        print("No import entrypoints found inside this workflow block.")
        print('Expected lines like: import: "from some.module import symbol"')
        return 0

    print("Entrypoints (public imports):")
    for r in refs:
        print(f"- {r.import_stmt}")
    print()

    print("Indexed signatures:")
    missing: list[str] = []
    for r in refs:
        entry = by_import_path.get(r.import_path)
        if entry is None:
            missing.append(r.import_path)
            continue

        sig = entry.get("signature")
        doc = entry.get("doc_summary")
        print(f"- {r.import_path}")
        if isinstance(sig, str) and sig:
            print(f"  signature: {sig}")
        else:
            print("  signature: <missing in api_index.json>")
        if isinstance(doc, str) and doc:
            print(f"  doc_summary: {doc}")
        print()

    if missing:
        print("WARNING: Some entrypoints were not found in llm/api_index.json:")
        for mp in missing:
            print(f"- {mp}")
        print()
        print("This usually means the symbol is not public (__all__) or the index is stale.")
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
