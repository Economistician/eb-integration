import numpy as np
import pandas as pd
import pytest

import eb_evaluation as ev
import eb_metrics as m


def test_cwsl_array_and_df_match():
    y = np.array([10, 12, 9, 11], dtype=float)
    yhat = np.array([9, 12, 10, 8], dtype=float)

    cwsl_arr = m.cwsl(y, yhat, cu=2.0, co=1.0)

    df = pd.DataFrame({"y": y, "yhat": yhat})
    cwsl_df = ev.compute_cwsl_df(df, y_true_col="y", y_pred_col="yhat", cu=2.0, co=1.0)

    # Assert both are float types
    assert isinstance(cwsl_arr, float), (
        f"Expected cwsl_arr to be of type float, but got {type(cwsl_arr)}"
    )
    assert isinstance(cwsl_df, float), (
        f"Expected cwsl_df to be of type float, but got {type(cwsl_df)}"
    )

    # Check if the two results match within a tolerance
    assert cwsl_arr == pytest.approx(cwsl_df, rel=1e-9), (
        f"Expected cwsl values to match but got {cwsl_arr} and {cwsl_df}"
    )


def test_evaluate_panel_df_smoke():
    df = pd.DataFrame(
        {
            "store": [101, 101, 202, 202],
            "date": ["2025-01-01", "2025-01-02", "2025-01-01", "2025-01-02"],
            "y": [10, 12, 9, 11],
            "yhat": [9, 12, 10, 8],
        }
    )

    levels = {"overall": [], "by_store": ["store"]}

    out = ev.evaluate_panel_df(
        df,
        levels=levels,
        actual_col="y",
        forecast_col="yhat",
        cu=2.0,
        co=1.0,
        tau=1.0,
    )

    # basic shape/contract checks
    assert {"level", "metric", "value"}.issubset(out.columns), (
        f"Expected columns ['level', 'metric', 'value'], but got {list(out.columns)}"
    )
    assert (out["level"] == "overall").any(), "Expected 'overall' level to be present in the output"
    assert (out["level"] == "by_store").any(), (
        "Expected 'by_store' level to be present in the output"
    )

    # ensure key metrics are present
    metrics = set(out["metric"].unique())
    assert "cwsl" in metrics, f"Expected 'cwsl' in metrics, but found {metrics}"
    assert "frs" in metrics, f"Expected 'frs' in metrics, but found {metrics}"
    assert "wmape" in metrics, f"Expected 'wmape' in metrics, but found {metrics}"
    assert "hr_at_tau" in metrics, f"Expected 'hr_at_tau' in metrics, but found {metrics}"
