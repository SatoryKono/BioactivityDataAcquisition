"""Stream A leftovers: logging, prometheus labels, DQ contracts, schemas, retention."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.infrastructure.config import dq_contract_config_loader as dq_loader
from bioetl.infrastructure.observability import logging_config as logging_mod
from bioetl.infrastructure.observability._prometheus_metric_label_normalizers import (
    _normalize_endpoint_segment,
    normalize_composite_phase_error_kind,
    normalize_composite_phase_loss_kind,
    normalize_composite_phase_retry_kind,
    normalize_observability_component,
    normalize_structural_action,
    normalize_structural_comparison,
)
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
from bioetl.infrastructure.storage.support import retention as retention_mod
from bioetl.infrastructure.storage.support.retention import RetentionPolicy

pytestmark = pytest.mark.unit


def test_mask_log_value_list_and_tuple() -> None:
    assert logging_mod._mask_log_value(["token"], field_name="note") == ["token"]
    masked_list = logging_mod._mask_log_value(["Bearer secret"], field_name="body")
    assert isinstance(masked_list, list)
    assert logging_mod._mask_log_value(("x",), field_name="body") == ("x",)


def test_trace_identifiers_none_invalid_and_non_int(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(
        __import__("sys").modules,
        "opentelemetry.trace",
        SimpleNamespace(get_current_span=lambda: None),
    )
    assert logging_mod._get_current_trace_identifiers() is None

    def _boom() -> object:
        raise RuntimeError("span gone")

    monkeypatch.setitem(
        __import__("sys").modules,
        "opentelemetry.trace",
        SimpleNamespace(get_current_span=_boom),
    )
    assert logging_mod._get_current_trace_identifiers() is None

    monkeypatch.setitem(
        __import__("sys").modules,
        "opentelemetry.trace",
        SimpleNamespace(
            get_current_span=lambda: SimpleNamespace(
                get_span_context=lambda: SimpleNamespace(
                    trace_id="abc",
                    span_id=1,
                    is_valid=True,
                )
            )
        ),
    )
    assert logging_mod._get_current_trace_identifiers() is None

    monkeypatch.setitem(
        __import__("sys").modules,
        "opentelemetry.trace",
        SimpleNamespace(
            get_current_span=lambda: SimpleNamespace(
                get_span_context=lambda: SimpleNamespace(
                    trace_id=0,
                    span_id=1,
                    is_valid=True,
                )
            )
        ),
    )
    assert logging_mod._get_current_trace_identifiers() is None


def test_resolve_log_file_empty_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BIOETL_LOG_FILE", "   ")
    assert logging_mod._resolve_log_file_path() is None


def test_prometheus_remaining_normalizers() -> None:
    assert normalize_composite_phase_error_kind("nope") == "other"
    assert normalize_composite_phase_loss_kind("nope") == "other"
    assert normalize_composite_phase_retry_kind("nope") == "other"
    assert normalize_observability_component("nope") == "other"
    assert normalize_structural_action("nope") == "other"
    assert normalize_structural_comparison("nope") == "other"
    assert _normalize_endpoint_segment("10.1000/xyz") == "{id}"
    assert _normalize_endpoint_segment("{chembl_id}") == "{chembl_id}"
    assert _normalize_endpoint_segment("activity") == "activity"


def test_dq_contract_identity_and_payload_edges(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="missing pipeline"):
        dq_loader._require_registry_identity_value(
            field_name="pipeline",
            contract_ref="chembl.activity",
            identity_data={},
            registry_entry={},
        )
    assert dq_loader._parse_disposition_overrides(None) == {}
    json_path = tmp_path / "c.json"
    json_path.write_text("[]", encoding="utf-8")
    assert dq_loader._load_contract_payload(json_path) == {}
    mapping = tmp_path / "ok.json"
    mapping.write_text(json.dumps({"a": 1}), encoding="utf-8")
    assert dq_loader._load_contract_payload(mapping) == {"a": 1}
    loader = dq_loader.DQContractConfigLoader(tmp_path)
    with pytest.raises(ValueError, match="Invalid pipeline name"):
        loader.load_dq_config_for_pipeline("nolevel")

    def _raise_mapping(_path: Path) -> object:
        raise ValueError("entries must be a mapping")

    monkey_loader = dq_loader.DQContractConfigLoader(tmp_path)
    from unittest.mock import patch

    with patch.object(
        dq_loader, "load_contract_registry_entries", _raise_mapping
    ), pytest.raises(ValueError, match="entries must be a mapping"):
        monkey_loader._lookup_registry_entry("chembl.activity")


def test_pipeline_yaml_config_validator_edges() -> None:
    host = PipelineYamlConfig.model_construct(
        business_primary_keys=None,
        technical_primary_key="activity_id",
        entity_type="publication",
        provider="chembl",
    )
    assert host.serialize_data_schema(None) is None
    with pytest.raises(ValueError, match="lowercase"):
        PipelineYamlConfig.validate_provider("Chembl")
    assert PipelineYamlConfig.reject_semantic_silver_filters("scalar") == "scalar"
    with pytest.raises(ValueError, match="business_primary_keys is required"):
        host._validate_primary_key_presence()
    host.business_primary_keys = ("activity_id", "extra")
    with pytest.raises(ValueError, match="MUST NOT be part"):
        host._validate_technical_key_separation()
    returned = host.validate_entity_type_canonical()
    assert returned is host


@pytest.mark.asyncio
async def test_retention_dedup_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    policy = RetentionPolicy(tmp_path, deduplicate_timeout_seconds=0.01)
    monkeypatch.setattr(retention_mod, "get_table_path", lambda *_a, **_k: str(tmp_path))
    monkeypatch.setattr(
        retention_mod, "deduplicate_delta_rows", lambda *_a, **_k: 0
    )
    times = iter([0.0, 1.0])
    monkeypatch.setattr(retention_mod.time, "perf_counter", lambda: next(times))

    async def _thread(fn: object, *args: object) -> object:
        del fn, args
        return 0

    monkeypatch.setattr(retention_mod.asyncio, "to_thread", _thread)
    with pytest.raises(TimeoutError, match="timed out"):
        await policy.deduplicate_silver("chembl/activity", ["id"])
    times_ok = iter([0.0, 0.0])
    monkeypatch.setattr(retention_mod.time, "perf_counter", lambda: next(times_ok))
    assert await policy.deduplicate_silver("chembl/activity", ["id"]) == 0
