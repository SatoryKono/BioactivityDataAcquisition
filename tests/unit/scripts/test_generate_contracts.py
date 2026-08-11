"""Regression tests for Gold contract generator check mode."""

from __future__ import annotations

import json

import pytest

from scripts.schema.generation import generate_contracts as generator

pytestmark = pytest.mark.unit


def test_check_mode_reports_current_without_writes(tmp_path, monkeypatch) -> None:
    artifact = tmp_path / "contract.json"
    artifact.write_text("expected\n", encoding="utf-8")
    monkeypatch.setattr(generator, "CONTRACTS_DIR", tmp_path)
    monkeypatch.setattr(
        generator, "_expected_artifacts", lambda: {artifact: "expected\n"}
    )
    before = artifact.stat().st_mtime_ns

    assert generator.generate_contracts(check=True) == 0
    assert artifact.read_text(encoding="utf-8") == "expected\n"
    assert artifact.stat().st_mtime_ns == before


def test_check_mode_reports_stale_without_writes(tmp_path, monkeypatch) -> None:
    artifact = tmp_path / "contract.json"
    artifact.write_text("stale\n", encoding="utf-8")
    monkeypatch.setattr(generator, "CONTRACTS_DIR", tmp_path)
    monkeypatch.setattr(
        generator, "_expected_artifacts", lambda: {artifact: "expected\n"}
    )

    assert generator.generate_contracts(check=True) == 1
    assert artifact.read_text(encoding="utf-8") == "stale\n"


def test_main_rejects_unknown_option() -> None:
    with pytest.raises(SystemExit) as exc_info:
        generator.main(["--unsupported"])

    assert exc_info.value.code == 2


def test_boolean_dtype_alias_maps_to_json_boolean() -> None:
    """Pandera's nullable Boolean dtype must not degrade to JSON object."""
    assert generator._map_dtype_to_json_type("boolean") == "boolean"


def test_composite_nullable_integer_contract_overrides_remain_integer() -> None:
    """Physical float compatibility must not weaken semantic integer contracts."""
    artifacts = generator._expected_artifacts()
    contract_path = generator.CONTRACTS_DIR / "composite_activity_v1.0.json"
    contract = json.loads(artifacts[contract_path])

    assert contract["properties"]["taxonomy_id"]["type"] == ["integer", "null"]
    assert contract["properties"]["record_id"]["type"] == ["integer", "null"]
    assert contract["properties"]["src_id"]["type"] == ["integer", "null"]


def test_expected_artifacts_are_reproducible_without_historical_diff_state(
    tmp_path, monkeypatch
) -> None:
    """Expected output must depend only on schemas, never previous file contents."""
    monkeypatch.setattr(generator, "CONTRACTS_DIR", tmp_path)
    first = generator._expected_artifacts()
    for path, content in first.items():
        path.write_text(content, encoding="utf-8")

    assert generator._expected_artifacts() == first
