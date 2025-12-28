"""
Tests for tooling/check.py.

These tests intentionally DO NOT run ruff/pyright/pre-commit/pytest for real.
They validate the runner's control-flow and command construction by mocking
the internal _run() helper.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Callable

import importlib.util
import sys

import pytest


def _load_check_module() -> ModuleType:
    """
    Load tooling/check.py as a module even if tooling/ isn't a Python package.

    This keeps eb-integration free of __init__.py requirements in tooling/.
    """
    repo_root = Path(__file__).resolve().parents[1]
    check_path = repo_root / "tooling" / "check.py"
    if not check_path.is_file():
        raise RuntimeError(f"Expected check.py at {check_path}")

    spec = importlib.util.spec_from_file_location("eb_integration_tooling_check", check_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not create import spec for tooling/check.py")

    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@dataclass(frozen=True)
class FakeProc:
    args: list[str]
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""


def _mk_fake_run(
    responses: Callable[[list[str]], FakeProc],
    seen: list[list[str]],
) -> Callable[..., FakeProc]:
    def _fake_run(cmd: list[str], *, cwd: Path) -> FakeProc:  # matches _run signature
        seen.append(list(cmd))
        return responses(list(cmd))

    return _fake_run


def _run_main(mod: ModuleType, monkeypatch: pytest.MonkeyPatch, argv: list[str]) -> int:
    # check.py uses argparse on sys.argv, so patch it.
    monkeypatch.setattr(sys, "argv", argv)
    return int(mod.main())


def test_find_repo_root_walks_up(tmp_path: Path) -> None:
    mod = _load_check_module()

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")

    nested = repo / "a" / "b" / "c"
    nested.mkdir(parents=True)

    root = mod._find_repo_root(nested)
    assert root == repo


def test_main_happy_path_calls_expected_steps(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load_check_module()

    # Ensure repo root detection resolves to the actual eb-integration repo
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.setattr(mod, "_find_repo_root", lambda _start: repo_root)

    seen: list[list[str]] = []

    def responses(cmd: list[str]) -> FakeProc:
        # Everything passes
        return FakeProc(args=cmd, returncode=0)

    monkeypatch.setattr(mod, "_run", _mk_fake_run(responses, seen))

    rc = _run_main(mod, monkeypatch, ["check.py"])
    assert rc == 0

    # Sanity: we ran ruff format check, ruff check, final format check, pyright, pre-commit, pytest
    joined = [" ".join(c) for c in seen]

    assert any(j.startswith("ruff format --check") for j in joined)
    assert any(j.startswith("ruff check") and "--fix" not in j for j in joined)
    assert any(j.startswith("ruff format --check") for j in joined)  # final check also
    assert any(j.startswith("pyright -p") for j in joined)
    assert any(" -m pre_commit run --all-files " in j for j in joined)
    assert any(j.strip() == "pytest" for j in joined)


def test_main_applies_format_fix_when_needed(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load_check_module()
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.setattr(mod, "_find_repo_root", lambda _start: repo_root)

    seen: list[list[str]] = []
    state = {"format_check_calls": 0}

    def responses(cmd: list[str]) -> FakeProc:
        cmd_s = " ".join(cmd)
        if cmd_s.startswith("ruff format --check"):
            state["format_check_calls"] += 1
            # First check fails -> triggers fix. Second check passes.
            return FakeProc(args=cmd, returncode=1 if state["format_check_calls"] == 1 else 0)
        return FakeProc(args=cmd, returncode=0)

    monkeypatch.setattr(mod, "_run", _mk_fake_run(responses, seen))

    rc = _run_main(mod, monkeypatch, ["check.py"])
    assert rc == 0

    joined = [" ".join(c) for c in seen]
    assert any(j.startswith("ruff format .") for j in joined), "Expected ruff format fix run"


def test_main_applies_lint_fix_when_needed(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load_check_module()
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.setattr(mod, "_find_repo_root", lambda _start: repo_root)

    seen: list[list[str]] = []
    state = {"lint_check_calls": 0}

    def responses(cmd: list[str]) -> FakeProc:
        cmd_s = " ".join(cmd)
        if cmd_s.startswith("ruff check") and "--fix" not in cmd_s:
            state["lint_check_calls"] += 1
            # First lint check fails -> triggers --fix; post-fix check passes.
            return FakeProc(args=cmd, returncode=1 if state["lint_check_calls"] == 1 else 0)
        return FakeProc(args=cmd, returncode=0)

    monkeypatch.setattr(mod, "_run", _mk_fake_run(responses, seen))

    rc = _run_main(mod, monkeypatch, ["check.py"])
    assert rc == 0

    joined = [" ".join(c) for c in seen]
    assert any("ruff check . --fix" in j for j in joined), "Expected ruff check --fix run"


def test_main_no_fix_mode_fails_on_first_format_error(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load_check_module()
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.setattr(mod, "_find_repo_root", lambda _start: repo_root)

    seen: list[list[str]] = []

    def responses(cmd: list[str]) -> FakeProc:
        if "ruff format --check" in " ".join(cmd):
            return FakeProc(args=cmd, returncode=1, stderr="Would reformat")
        return FakeProc(args=cmd, returncode=0)

    monkeypatch.setattr(mod, "_run", _mk_fake_run(responses, seen))

    rc = _run_main(mod, monkeypatch, ["check.py", "--no-fix"])
    assert rc == 1


def test_precommit_reruns_once_when_first_pass_changes_or_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod = _load_check_module()
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.setattr(mod, "_find_repo_root", lambda _start: repo_root)

    seen: list[list[str]] = []
    state = {"precommit_calls": 0}

    def responses(cmd: list[str]) -> FakeProc:
        cmd_s = " ".join(cmd)
        if " -m pre_commit run --all-files " in cmd_s:
            state["precommit_calls"] += 1
            # first pass fails -> second pass passes
            return FakeProc(args=cmd, returncode=1 if state["precommit_calls"] == 1 else 0)
        return FakeProc(args=cmd, returncode=0)

    monkeypatch.setattr(mod, "_run", _mk_fake_run(responses, seen))

    rc = _run_main(mod, monkeypatch, ["check.py"])
    assert rc == 0
    assert state["precommit_calls"] == 2


def test_skip_flags_skip_precommit_and_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load_check_module()
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.setattr(mod, "_find_repo_root", lambda _start: repo_root)

    seen: list[list[str]] = []

    def responses(cmd: list[str]) -> FakeProc:
        return FakeProc(args=cmd, returncode=0)

    monkeypatch.setattr(mod, "_run", _mk_fake_run(responses, seen))

    rc = _run_main(mod, monkeypatch, ["check.py", "--skip-precommit", "--skip-tests"])
    assert rc == 0

    joined = [" ".join(c) for c in seen]
    assert not any(" -m pre_commit run --all-files " in j for j in joined)
    assert not any(j.strip() == "pytest" for j in joined)
