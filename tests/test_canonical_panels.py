from __future__ import annotations

from collections.abc import Callable
import importlib.util
from typing import Any

import numpy as np
import pandas as pd
import pytest


def _has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _import_attr(module_path: str, attr: str) -> Any:
    module = __import__(module_path, fromlist=[attr])
    return getattr(module, attr)


def _import_panel_demand_v1() -> type:
    # Canonical import path used by ecosystem smoke tests.
    return _import_attr(
        "eb_contracts.contracts.demand_panel.v1.panel_demand",
        "PanelDemandV1",
    )


def _import_panel_point_forecast_v1() -> type:
    """Import PanelPointForecastV1 from its canonical eb-contracts location."""
    return _import_attr(
        "eb_contracts.contracts.forecast_panel.v1.forecast_panel",
        "PanelPointForecastV1",
    )


def _resolve_validator(validate_module: Any, names: list[str]) -> Callable[..., Any]:
    """Resolve a validator from ``eb_contracts.api.validate`` by preferred name order."""
    for name in names:
        fn = getattr(validate_module, name, None)
        if callable(fn):
            return fn
    raise AttributeError(f"None of the validator names exist: {names}")


def make_canonical_panel_demand_v1() -> Any:
    """
    Canonical tiny timestamp demand panel that encodes:
    - normal observable intervals with numeric y
    - a structural-zero interval with y null and is_observable False
    """
    PanelDemandV1 = _import_panel_demand_v1()

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

    return PanelDemandV1.from_frame(
        df,
        keys=["store_id", "forecast_entity_id"],
        y_col="y",
        time_mode="timestamp",
        ts_col="ts",
    )


def make_canonical_panel_point_forecast_v1() -> Any:
    """Canonical timestamp point-forecast panel aligned to the demand panel.

    ``PanelPointForecastV1`` uses fixed columns
    (``entity_id``, ``interval_start``, ``y_true``, ``y_pred``);
    ``from_frame()`` does not accept column remapping.
    """
    PanelPointForecastV1 = _import_panel_point_forecast_v1()

    # Contract canonical column names.
    df = pd.DataFrame(
        [
            {
                "entity_id": "0001:101",
                "interval_start": pd.Timestamp("2026-01-01 00:00:00", tz="UTC"),
                "y_true": 10.0,
                "y_pred": 11.0,
            },
            {
                "entity_id": "0001:101",
                "interval_start": pd.Timestamp("2026-01-01 00:30:00", tz="UTC"),
                "y_true": 12.0,
                "y_pred": 12.5,
            },
            # Forecasts can exist even when demand is not observable; evaluation
            # should use demand observability to filter. Contract allows it.
            {
                "entity_id": "0001:101",
                "interval_start": pd.Timestamp("2026-01-01 01:00:00", tz="UTC"),
                "y_true": np.nan,
                "y_pred": 0.0,
            },
        ]
    )

    return PanelPointForecastV1.from_frame(df)


@pytest.mark.ecosystem
@pytest.mark.skipif(not _has_module("eb_contracts"), reason="eb-contracts not installed")
def test_canonical_panel_demand_v1_validates() -> None:
    from eb_contracts.api import validate as v  # type: ignore[reportMissingImports]

    panel = make_canonical_panel_demand_v1()

    validate_panel_demand = _resolve_validator(v, ["panel_demand_v1", "validate_panel_demand_v1"])
    validate_panel_demand(panel)


@pytest.mark.ecosystem
@pytest.mark.skipif(not _has_module("eb_contracts"), reason="eb-contracts not installed")
def test_canonical_panel_point_forecast_v1_validates() -> None:
    """Construct and validate a canonical point-forecast panel via ``panel_point_v1``."""
    from eb_contracts.api import validate as v  # type: ignore[reportMissingImports]

    panel = make_canonical_panel_point_forecast_v1()

    validate_point_forecast = _resolve_validator(
        v,
        [
            "panel_point_v1",
            # Alternate names kept for resolver tolerance:
            "panel_point_forecast_v1",
            "validate_panel_point_forecast_v1",
        ],
    )

    # panel_point_v1 expects a DataFrame; reconstruct from the panel frame when needed.
    if validate_point_forecast.__name__ == "panel_point_v1":
        frame = panel.frame  # contract object should expose .frame
        _ = validate_point_forecast(frame)
    else:
        validate_point_forecast(panel)
