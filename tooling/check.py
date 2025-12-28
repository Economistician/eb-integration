"""
EB local validation runner.

This script is intended to provide a single command that performs a full local validation
pass with CI parity across the Electric Barometer ecosystem.

Default behavior:
- Check formatting; if needed, apply formatting.
- Check lint; if needed, apply safe fixes.
- Re-check formatting and lint after fixes.
- Run Pyright type checking (whole repo; auto-skip if no Python files).
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


def _has_python_files(repo_root: Path) -> bool:
    """Return True if repo contains any Python files (excluding common vendor/build dirs)."""
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
        return True
    return False


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

    print(f"Repo root:   {repo_root}")
    print(f"Tooling dir: {tooling_dir}")
    print(f"Fix enabled: {fix_enabled}")

    try:
        # -------------------------
        # Ruff format (check, then fix if needed)
        # -------------------------
        proc = _run(["ruff", "format", "--check", ".", "--config", str(ruff_config)], cwd=repo_root)
        if proc.returncode != 0:
            if not fix_enabled:
                _require_ok(proc, step="ruff format --check")
            print("\nFormatting needed; applying ruff format ...")
            _require_ok(
                _run(["ruff", "format", ".", "--config", str(ruff_config)], cwd=repo_root),
                step="ruff format",
            )
            _require_ok(
                _run(
                    ["ruff", "format", "--check", ".", "--config", str(ruff_config)], cwd=repo_root
                ),
                step="ruff format --check (post-fix)",
            )
        else:
            _print_proc(proc)

        # -------------------------
        # Ruff lint (check, then fix if needed)
        # -------------------------
        proc = _run(["ruff", "check", ".", "--config", str(ruff_config)], cwd=repo_root)
        if proc.returncode != 0:
            if not fix_enabled:
                _require_ok(proc, step="ruff check")
            print("\nLint issues found; applying ruff check --fix ...")
            _require_ok(
                _run(["ruff", "check", ".", "--fix", "--config", str(ruff_config)], cwd=repo_root),
                step="ruff check --fix",
            )
            _require_ok(
                _run(["ruff", "check", ".", "--config", str(ruff_config)], cwd=repo_root),
                step="ruff check (post-fix)",
            )
        else:
            _print_proc(proc)

        # -------------------------
        # Ruff format (final check)
        # -------------------------
        _require_ok(
            _run(["ruff", "format", "--check", ".", "--config", str(ruff_config)], cwd=repo_root),
            step="ruff format --check (final)",
        )

        # -------------------------
        # Pyright (type check) - whole repo, skip if no Python exists
        # -------------------------
        if not _has_python_files(repo_root):
            print("\n⏭️  Skipping pyright (no .py files found in repo).")
        else:
            _require_ok(
                _run(["pyright", "-p", str(pyright_config), "."], cwd=repo_root),
                step="pyright",
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
            _require_ok(_run(["pytest"], cwd=repo_root), step="pytest")

    except RuntimeError as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        return 1

    print("\n✅ All checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
