"""
Build a single deterministic LLM bundle for live sessions.

The bundle concatenates:
- llm/system.txt        (rules / behavior constraints)
- llm/workflows.yml     (canonical workflows)
- llm/llm-bundle.yml    (bundle metadata / intent)
- llm/repo_index.json   (ecosystem repository map)
- llm/api_index.json    (public API surface)

Output is a single text file suitable for copy/paste into a new chat.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def _repo_root() -> Path:
    # tooling/llm_bundle.py -> repo root
    return Path(__file__).resolve().parents[1]


def _read(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    return path.read_text(encoding="utf-8").rstrip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build a single LLM bundle from system.txt, workflows.yml, "
            "llm-bundle.yml, repo_index.json, and api_index.json"
        )
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Output bundle path (e.g., llm/bundle.txt)",
    )
    args = parser.parse_args(argv)

    root = _repo_root()
    llm_dir = root / "llm"

    system_path = llm_dir / "system.txt"
    workflows_path = llm_dir / "workflows.yml"
    bundle_meta_path = llm_dir / "llm-bundle.yml"
    repo_index_path = llm_dir / "repo_index.json"
    api_index_path = llm_dir / "api_index.json"

    system_txt = _read(system_path)
    workflows_txt = _read(workflows_path)
    bundle_meta_txt = _read(bundle_meta_path)

    repo_index = json.loads(_read(repo_index_path))
    api_index = json.loads(_read(api_index_path))

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    bundle: list[str] = []

    bundle.append("# ===============================")
    bundle.append("# Electric Barometer — LLM SYSTEM")
    bundle.append("# ===============================")
    bundle.append(system_txt)
    bundle.append("")

    bundle.append("# ===============================")
    bundle.append("# Electric Barometer — WORKFLOWS")
    bundle.append("# ===============================")
    bundle.append(workflows_txt)
    bundle.append("")

    bundle.append("# ===============================")
    bundle.append("# Electric Barometer — LLM BUNDLE METADATA")
    bundle.append("# ===============================")
    bundle.append(bundle_meta_txt)
    bundle.append("")

    bundle.append("# ===============================")
    bundle.append("# Electric Barometer — REPO INDEX")
    bundle.append("# ===============================")
    bundle.append(json.dumps(repo_index, indent=2, sort_keys=True))
    bundle.append("")

    bundle.append("# ===============================")
    bundle.append("# Electric Barometer — API INDEX")
    bundle.append("# ===============================")
    bundle.append(json.dumps(api_index, indent=2, sort_keys=True))

    out_path.write_text("\n".join(bundle) + "\n", encoding="utf-8")

    print(f"Wrote LLM bundle: {out_path}")
    print(
        "Contents: "
        "system.txt + workflows.yml + llm-bundle.yml + repo_index.json + api_index.json "
        f"(api_entries={len(api_index.get('entries', []))}, "
        f"repos={len(repo_index.get('repos', []))})"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
