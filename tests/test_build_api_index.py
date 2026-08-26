"""Tests for tooling/build_api_index.py golden-file determinism."""

from __future__ import annotations

from enum import Enum
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType
from typing import Any


def _load_builder() -> ModuleType:
    script = Path(__file__).resolve().parents[1] / "tooling" / "build_api_index.py"
    spec = importlib.util.spec_from_file_location("eb_integration_tooling_build_api_index", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {script}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _index_exports(builder: ModuleType, *, name: str, obj: object) -> Any:
    mod = ModuleType("fake_pkg")
    mod.__dict__["__all__"] = [name]
    setattr(mod, name, obj)
    entries: list[Any] = []
    builder._index_module_exports("fake_pkg", mod, entries)
    assert len(entries) == 1
    return entries[0]


def test_build_api_index_omits_runner_specific_fields() -> None:
    payload = _load_builder().build_api_index([])
    assert "generated_at_utc" not in payload
    assert "python_version" not in payload.get("ecosystem", {})
    assert "diagnostics" not in payload


def test_build_api_index_is_bit_stable_across_calls() -> None:
    builder = _load_builder()
    first = json.dumps(builder.build_api_index([]), sort_keys=True)
    second = json.dumps(builder.build_api_index([]), sort_keys=True)
    assert first == second


def test_build_api_index_omits_diagnostics_for_missing_packages() -> None:
    payload = _load_builder().build_api_index(["definitely_not_an_eb_package"])
    assert "diagnostics" not in payload
    assert payload["ecosystem"]["packages_indexed"] == []
    assert payload["entries"] == []


def test_repo_index_skips_non_catalog_packages() -> None:
    root = Path(__file__).resolve().parents[1]
    pkgs, _diag = _load_builder()._packages_from_repo_index(root)
    assert "eb_examples" not in pkgs
    assert "eb_contracts" in pkgs
    assert "electric_barometer" in pkgs


def test_enum_class_signature_is_omitted() -> None:
    class Color(Enum):
        RED = 1

    entry = _index_exports(_load_builder(), name="Color", obj=Color)
    assert entry.signature is None
    assert entry.name == "Color"


def test_builtin_origin_doc_and_signature_are_omitted() -> None:
    entry = _index_exports(_load_builder(), name="Scale", obj=float)
    assert entry.doc_summary is None
    assert entry.signature is None
    assert entry.io == {"defined_in": "builtins"}
