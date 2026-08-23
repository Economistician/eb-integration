"""Tests for tooling/check_ecosystem.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType

import pytest


def _load_ecosystem_module() -> ModuleType:
    """Load tooling/check_ecosystem.py even if tooling/ is not a Python package."""
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / "tooling" / "check_ecosystem.py"
    if not script.is_file():
        raise RuntimeError(f"Expected check_ecosystem.py at {script}")

    spec = importlib.util.spec_from_file_location("eb_integration_tooling_check_ecosystem", script)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not create import spec for tooling/check_ecosystem.py")

    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _write_pyproject(
    repo: Path,
    *,
    name: str,
    requires_python: str = ">=3.11",
    dependencies: list[str] | None = None,
    ecosystem_marker: bool = False,
) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    deps = dependencies or []
    dep_lines = ",\n  ".join(f'"{item}"' for item in deps)
    marker_block = ""
    if ecosystem_marker:
        marker_block = """
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
  "ecosystem: cross-package integration smoke tests",
]
"""
    (repo / "pyproject.toml").write_text(
        f"""[project]
name = "{name}"
version = "0.0.0"
requires-python = "{requires_python}"
dependencies = [
  {dep_lines}
]
{marker_block}""",
        encoding="utf-8",
    )


def _write_src_module(repo: Path, package: str, body: str) -> Path:
    src = repo / "src" / package
    src.mkdir(parents=True, exist_ok=True)
    path = src / "__init__.py"
    path.write_text(body, encoding="utf-8")
    return path


def _try_symlink_tooling(repo: Path, integration: Path) -> bool:
    target = Path("..") / "eb-integration" / "tooling"
    link = repo / "tooling"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        return False
    return link.is_symlink() and link.resolve() == (integration / "tooling").resolve()


def _make_workspace(tmp_path: Path) -> tuple[Path, Path]:
    eco = tmp_path / "workspace"
    integration = eco / "eb-integration"
    _write_pyproject(integration, name="eb-integration", ecosystem_marker=True)
    (integration / "tooling").mkdir(parents=True)
    (integration / "tests").mkdir(parents=True)
    return eco, integration


def _passing_pytest(**_kwargs: object) -> int:
    return 0


def test_requirement_distribution_name_strips_markers_and_extras() -> None:
    mod = _load_ecosystem_module()
    assert mod.requirement_distribution_name("eb-metrics>=0.2,<0.3") == "eb-metrics"
    assert mod.requirement_distribution_name("eb-metrics[sklearn]>=0.2,<0.3") == "eb-metrics"
    assert (
        mod.requirement_distribution_name("eb-metrics @ git+https://example.com/eb-metrics.git")
        == "eb-metrics"
    )
    assert mod.requirement_distribution_name("  # comment") is None
    assert mod.canonicalize_name("eb_metrics") == "eb-metrics"
    assert mod.canonicalize_name("electric_barometer") == "electric-barometer"


def test_ecosystem_imports_detect_from_and_import_forms(tmp_path: Path) -> None:
    mod = _load_ecosystem_module()
    path = tmp_path / "mod.py"
    path.write_text(
        "from __future__ import annotations\n"
        "import eb_metrics.metrics as metrics\n"
        "from eb_evaluation.diagnostics import validate_governance\n"
        "from electric_barometer import __version__\n"
        "from .electric_barometer import ElectricBarometer\n"
        "import numpy as np\n",
        encoding="utf-8",
    )
    assert mod.ecosystem_imports_in_source(path) == {
        "eb_metrics",
        "eb_evaluation",
        "electric_barometer",
    }


def test_try_except_and_relative_imports_are_not_required(tmp_path: Path) -> None:
    mod = _load_ecosystem_module()
    path = tmp_path / "optional.py"
    path.write_text(
        "from __future__ import annotations\n"
        "from .electric_barometer import ElectricBarometer\n"
        "try:\n"
        "    from eb_evaluation.diagnostics.dqc import classify_dqc\n"
        "except Exception:\n"
        "    classify_dqc = None\n",
        encoding="utf-8",
    )
    assert mod.ecosystem_imports_in_source(path) == set()


def test_audit_passes_when_imports_are_declared(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod = _load_ecosystem_module()
    monkeypatch.setattr(mod, "tooling_symlink_issues", lambda *_a, **_k: [])
    eco, integration = _make_workspace(tmp_path)
    metrics = eco / "eb-metrics"
    _write_pyproject(metrics, name="eb-metrics", dependencies=["numpy>=1.24"])
    _write_src_module(
        metrics,
        "eb_metrics",
        "from __future__ import annotations\nimport numpy as np\n",
    )
    evaluation = eco / "eb-evaluation"
    _write_pyproject(evaluation, name="eb-evaluation", dependencies=["eb-metrics>=0.2,<0.3"])
    _write_src_module(
        evaluation,
        "eb_evaluation",
        "from __future__ import annotations\nfrom eb_metrics.metrics import cwsl\n",
    )

    rc = mod.run_audit(
        ecosystem_root=eco,
        integration_root=integration,
        run_pytest=True,
        pytest_runner=_passing_pytest,
    )
    assert rc == 0


def test_audit_flags_undeclared_ecosystem_import(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod = _load_ecosystem_module()
    monkeypatch.setattr(mod, "tooling_symlink_issues", lambda *_a, **_k: [])
    eco, integration = _make_workspace(tmp_path)
    evaluation = eco / "eb-evaluation"
    _write_pyproject(evaluation, name="eb-evaluation", dependencies=["numpy>=1.24"])
    _write_src_module(
        evaluation,
        "eb_evaluation",
        "from __future__ import annotations\nfrom eb_metrics import mae\n",
    )

    rc = mod.run_audit(
        ecosystem_root=eco,
        integration_root=integration,
        run_pytest=False,
    )
    assert rc == 1


def test_self_imports_do_not_require_self_dependency(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod = _load_ecosystem_module()
    monkeypatch.setattr(mod, "tooling_symlink_issues", lambda *_a, **_k: [])
    eco, integration = _make_workspace(tmp_path)
    metrics = eco / "eb-metrics"
    _write_pyproject(metrics, name="eb-metrics", dependencies=["numpy>=1.24"])
    _write_src_module(
        metrics,
        "eb_metrics",
        "from __future__ import annotations\nfrom eb_metrics.metrics import cwsl\n",
    )

    rc = mod.run_audit(
        ecosystem_root=eco,
        integration_root=integration,
        run_pytest=False,
    )
    assert rc == 0


def test_requires_python_must_be_identical(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load_ecosystem_module()
    monkeypatch.setattr(mod, "tooling_symlink_issues", lambda *_a, **_k: [])
    eco, integration = _make_workspace(tmp_path)
    metrics = eco / "eb-metrics"
    _write_pyproject(metrics, name="eb-metrics", requires_python=">=3.12")
    _write_src_module(metrics, "eb_metrics", "from __future__ import annotations\n")

    rc = mod.run_audit(
        ecosystem_root=eco,
        integration_root=integration,
        run_pytest=False,
    )
    assert rc == 1


def test_missing_tooling_symlink_is_an_error(tmp_path: Path) -> None:
    mod = _load_ecosystem_module()
    eco, integration = _make_workspace(tmp_path)
    metrics = eco / "eb-metrics"
    _write_pyproject(metrics, name="eb-metrics")
    _write_src_module(metrics, "eb_metrics", "from __future__ import annotations\n")

    rc = mod.run_audit(
        ecosystem_root=eco,
        integration_root=integration,
        run_pytest=False,
    )
    assert rc == 1


def test_concrete_tooling_directory_is_rejected(tmp_path: Path) -> None:
    mod = _load_ecosystem_module()
    eco, integration = _make_workspace(tmp_path)
    metrics = eco / "eb-metrics"
    _write_pyproject(metrics, name="eb-metrics")
    (metrics / "tooling").mkdir(parents=True)

    issues = mod.tooling_symlink_issues(metrics, integration / "tooling")
    assert issues
    assert issues[0].kind == "symlink"


def test_require_siblings_fails_when_none_present(tmp_path: Path) -> None:
    mod = _load_ecosystem_module()
    eco, integration = _make_workspace(tmp_path)
    rc = mod.run_audit(
        ecosystem_root=eco,
        integration_root=integration,
        require_siblings=True,
        run_pytest=False,
    )
    assert rc == 2


def test_missing_siblings_are_skipped_without_require_flag(tmp_path: Path) -> None:
    mod = _load_ecosystem_module()
    eco, integration = _make_workspace(tmp_path)
    rc = mod.run_audit(
        ecosystem_root=eco,
        integration_root=integration,
        require_siblings=False,
        run_pytest=False,
    )
    assert rc == 0


def test_pytest_failure_fails_the_audit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load_ecosystem_module()
    monkeypatch.setattr(mod, "tooling_symlink_issues", lambda *_a, **_k: [])
    eco, integration = _make_workspace(tmp_path)
    metrics = eco / "eb-metrics"
    _write_pyproject(metrics, name="eb-metrics")
    _write_src_module(metrics, "eb_metrics", "from __future__ import annotations\n")

    def failing_pytest(*, cwd: Path, pythonpath: str) -> int:
        assert cwd == integration
        assert str((metrics / "src").resolve()) in pythonpath
        return 1

    rc = mod.run_audit(
        ecosystem_root=eco,
        integration_root=integration,
        pytest_runner=failing_pytest,
    )
    assert rc == 1


def test_pytest_exit_code_5_is_treated_as_no_tests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod = _load_ecosystem_module()
    monkeypatch.setattr(mod, "tooling_symlink_issues", lambda *_a, **_k: [])
    eco, integration = _make_workspace(tmp_path)
    metrics = eco / "eb-metrics"
    _write_pyproject(metrics, name="eb-metrics")
    _write_src_module(metrics, "eb_metrics", "from __future__ import annotations\n")

    rc = mod.run_audit(
        ecosystem_root=eco,
        integration_root=integration,
        pytest_runner=lambda **_k: 5,
    )
    assert rc == 0


def test_valid_tooling_symlink_is_accepted(tmp_path: Path) -> None:
    mod = _load_ecosystem_module()
    eco, integration = _make_workspace(tmp_path)
    metrics = eco / "eb-metrics"
    _write_pyproject(metrics, name="eb-metrics")
    _write_src_module(metrics, "eb_metrics", "from __future__ import annotations\n")
    if not _try_symlink_tooling(metrics, integration):
        pytest.skip("Cannot create directory symlinks in this environment")

    issues = mod.tooling_symlink_issues(metrics, integration / "tooling")
    assert issues == []


def test_sibling_checkouts_present_detects_named_dirs(tmp_path: Path) -> None:
    mod = _load_ecosystem_module()
    eco, integration = _make_workspace(tmp_path)
    tooling = integration / "tooling"
    assert mod.sibling_checkouts_present(tooling) is False
    (eco / "eb-metrics").mkdir()
    assert mod.sibling_checkouts_present(tooling) is True
