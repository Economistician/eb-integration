"""Tests for tooling/build_api_index.py golden-file determinism."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType


def _load_builder() -> ModuleType:
    script = Path(__file__).resolve().parents[1] / "tooling" / "build_api_index.py"
    spec = importlib.util.spec_from_file_location("eb_integration_tooling_build_api_index", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {script}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_build_api_index_omits_runner_specific_fields() -> None:
    payload = _load_builder().build_api_index([])
    assert "generated_at_utc" not in payload
    assert "python_version" not in payload.get("ecosystem", {})


def test_build_api_index_is_bit_stable_across_calls() -> None:
    builder = _load_builder()
    first = json.dumps(builder.build_api_index([]), sort_keys=True)
    second = json.dumps(builder.build_api_index([]), sort_keys=True)
    assert first == second
