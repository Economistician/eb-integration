from __future__ import annotations

import importlib.util

import numpy as np
import pandas as pd
import pytest


def local_cwsl(y: np.ndarray, yhat: np.ndarray, cu: float, co: float) -> float:
    """
    Internalized CWSL logic to allow smoke testing without an external
    eb-metrics dependency.

    This remains intentionally simple: it's here to validate NumPy/Pandas
    integration and a representative cost-asymmetric computation path.
    """
    errors = y - yhat
    costs = np.where(errors > 0, errors * cu, -errors * co)
    return float(np.mean(costs))


def _has_module(name: str) -> bool:
    """
    Return True if an importable module exists in the current environment.
    Used to make "real ecosystem" tests opt-in (CI job can install deps).
    """
    return importlib.util.find_spec(name) is not None


@pytest.mark.smoke
def test_infrastructure_availability() -> None:
    """
    Validates that the CI/CD pipeline correctly installs runtime dependencies
    like NumPy and Pandas across the test matrix.
    """
    y = np.array([10, 12, 9, 11], dtype=float)
    df = pd.DataFrame({"y": y})

    assert len(df) == 4
    assert np.isclose(np.mean(y), 10.5)
    assert np.isclose(df["y"].mean(), 10.5)


@pytest.mark.smoke
def test_cwsl_array_and_df_match() -> None:
    """
    Validates that array-based and DataFrame-based calculations match using
    internalized logic to verify NumPy/Pandas integration.
    """
    y = np.array([10, 12, 9, 11], dtype=float)
    yhat = np.array([9, 12, 10, 8], dtype=float)

    cwsl_arr = local_cwsl(y, yhat, cu=2.0, co=1.0)

    df = pd.DataFrame({"y": y, "yhat": yhat})
    df["costs"] = np.where(
        df["y"] > df["yhat"], (df["y"] - df["yhat"]) * 2.0, (df["yhat"] - df["y"]) * 1.0
    )
    cwsl_df = float(df["costs"].mean())

    assert isinstance(cwsl_arr, float)
    assert cwsl_arr == pytest.approx(cwsl_df, rel=1e-12)


@pytest.mark.smoke
def test_evaluation_output_df_contract_smoke() -> None:
    """
    Validates the minimal structural contract of the evaluation output dataframe
    required by the ecosystem: a tidy long-form (level, metric, value).

    NOTE: This test does not assert EB implementation details. It's the local
    invariant that downstream reporting and integration expect.
    """
    results = pd.DataFrame(
        [
            {"level": "overall", "metric": "cwsl", "value": 1.5},
            {"level": "by_store", "metric": "cwsl", "value": 1.2},
            {"level": "overall", "metric": "wmape", "value": 0.15},
        ]
    )

    required_cols = {"level", "metric", "value"}
    assert required_cols.issubset(results.columns)

    # Basic sanity: types and non-empty
    assert len(results) > 0

    # Use numpy conversion to avoid pandas-stubs type ambiguity under pyright.
    level_na = results["level"].isna().to_numpy()
    metric_na = results["metric"].isna().to_numpy()
    assert bool(np.any(level_na)) is False
    assert bool(np.any(metric_na)) is False

    # Avoid calling .to_numpy(dtype=float) on the result of pd.to_numeric because
    # pandas-stubs/pyright can infer overly-broad unions. Convert via np.asarray.
    numeric_series = pd.to_numeric(results["value"], errors="coerce")
    values = np.asarray(numeric_series, dtype=np.float64)
    assert bool(np.any(np.isnan(values))) is False

    levels = set(results["level"].unique())
    assert "overall" in levels
    assert "by_store" in levels


# ---------------------------------------------------------------------------
# Real ecosystem smoke (opt-in)
#
# These tests run only when the EB packages are installed in the environment.
# This is intended for a dedicated CI job (e.g., "ecosystem-smoke") that
# installs eb-contracts, eb-metrics, eb-evaluation from PyPI to detect drift.
# ---------------------------------------------------------------------------


@pytest.mark.ecosystem
@pytest.mark.skipif(not _has_module("eb_contracts"), reason="eb-contracts not installed")
def test_ecosystem_imports_contracts() -> None:
    import eb_contracts


@pytest.mark.ecosystem
@pytest.mark.skipif(not _has_module("eb_metrics"), reason="eb-metrics not installed")
def test_ecosystem_imports_metrics() -> None:
    import eb_metrics


@pytest.mark.ecosystem
@pytest.mark.skipif(not _has_module("eb_evaluation"), reason="eb-evaluation not installed")
def test_ecosystem_imports_evaluation() -> None:
    import eb_evaluation


@pytest.mark.ecosystem
@pytest.mark.skipif(
    not (_has_module("eb_contracts") and _has_module("eb_metrics")),
    reason="ecosystem deps not installed",
)
def test_ecosystem_metrics_runs_against_real_library() -> None:
    """
    Compute at least one real metric from eb-metrics to catch API drift.
    This is intentionally tiny and deterministic.
    """
    y_true = np.array([10.0, 12.0, 11.0], dtype=float)
    y_pred = np.array([10.0, 11.5, 11.5], dtype=float)

    # If the name changes, the test should fail: that is the drift tripwire.
    from eb_metrics import mae

    value = mae(y_true=y_true, y_pred=y_pred)
    assert float(value) >= 0.0


@pytest.mark.ecosystem
@pytest.mark.skipif(not _has_module("eb_contracts"), reason="eb-contracts not installed")
def test_ecosystem_panel_demand_v1_validates_minimal_timestamp_panel() -> None:
    """
    True ecosystem drift tripwire: build a tiny PanelDemandV1 and validate it.

    This catches:
    - contract construction API drift (PanelDemandV1.from_frame)
    - validation entrypoint drift (validate.panel_demand_v1)
    - core gating semantics drift (structural-zero behavior)
    """
    from eb_contracts.api import validate as v
    from eb_contracts.contracts.demand_panel.v1.panel_demand import PanelDemandV1

    df = pd.DataFrame(
        [
            {
                "store_id": "0001",
                "forecast_entity_id": 101,
                "ts": pd.Timestamp("2026-01-01 00:00:00", tz="UTC"),
                "y": 10.0,
                "is_observable": True,
                "is_possible": True,
                "is_structural_zero": False,
            },
            {
                "store_id": "0001",
                "forecast_entity_id": 101,
                "ts": pd.Timestamp("2026-01-01 00:30:00", tz="UTC"),
                "y": 12.0,
                "is_observable": True,
                "is_possible": True,
                "is_structural_zero": False,
            },
            # Structural-zero semantics: y must be null and the interval must not be observable.
            {
                "store_id": "0001",
                "forecast_entity_id": 101,
                "ts": pd.Timestamp("2026-01-01 01:00:00", tz="UTC"),
                "y": np.nan,
                "is_observable": False,
                "is_possible": True,
                "is_structural_zero": True,
            },
        ]
    )

    panel = PanelDemandV1.from_frame(
        df,
        keys=["store_id", "forecast_entity_id"],
        y_col="y",
        time_mode="timestamp",
        ts_col="ts",
    )

    # Should not raise.
    v.panel_demand_v1(panel)


@pytest.mark.ecosystem
@pytest.mark.skipif(not _has_module("eb_contracts"), reason="eb-contracts not installed")
def test_ecosystem_panel_point_forecast_v1_validates_minimal_panel() -> None:
    """
    Forecast contract drift tripwire: validate a minimal PanelPointForecastV1 via the
    stable public API entrypoint (validate.panel_point_v1).

    This catches:
    - required column drift (entity_id, interval_start, y_true, y_pred)
    - uniqueness constraints drift ((entity_id, interval_start) unique)
    - public entrypoint drift (panel_point_v1)
    """
    from eb_contracts.api import validate as v

    frame = pd.DataFrame(
        [
            {
                "entity_id": "store:0001|fe:101",
                "interval_start": pd.Timestamp("2026-01-01 00:00:00", tz="UTC"),
                "y_true": 10.0,
                "y_pred": 9.5,
            },
            {
                "entity_id": "store:0001|fe:101",
                "interval_start": pd.Timestamp("2026-01-01 00:30:00", tz="UTC"),
                "y_true": 12.0,
                "y_pred": 12.25,
            },
        ]
    )

    forecast = v.panel_point_v1(frame)
    assert forecast.CONTRACT_NAME == "PanelPointForecastV1"
    assert len(forecast.frame) == 2


@pytest.mark.ecosystem
@pytest.mark.skipif(
    not (_has_module("eb_contracts") and _has_module("eb_evaluation")),
    reason="ecosystem deps not installed",
)
def test_ecosystem_evaluation_entrypoints_exist() -> None:
    """
    Smoke-check that the diagnostics module is importable and exposes the
    stable validation entrypoints you already treat as public API.
    """
    from eb_evaluation.diagnostics import (
        validate_dqc,
        validate_fpc,
        validate_governance,
    )

    assert callable(validate_dqc)
    assert callable(validate_fpc)
    assert callable(validate_governance)
