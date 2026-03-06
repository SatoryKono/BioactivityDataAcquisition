"""Unit tests for BatchExecutor DQ helper mixin."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

import pytest

import bioetl.application.core.batch_executor_dq_mixin as dq_mixin_module
from bioetl.application.core.batch_executor_dq_mixin import _BatchExecutorDQMixin

pytestmark = pytest.mark.unit


@dataclass
class _Rule:
    field: str
    key_type: str
    nullable: bool


@dataclass
class _DQConfig:
    soft_fail_threshold: float = 0.1
    hard_fail_threshold: float = 0.3
    key_nullability_rules: list[_Rule] = field(default_factory=list)


@dataclass
class _TableConfig:
    silver_table: str | None = "silver_publication"
    primary_keys: tuple[str, ...] = ("entity_id",)
    gold_table: str | None = "gold_publication"


class _LoggerStub:
    def __init__(self) -> None:
        self.warning_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def warning(self, *args: object, **kwargs: object) -> None:
        self.warning_calls.append((args, kwargs))


class _BatchExecutorDQHarness(_BatchExecutorDQMixin):
    def __init__(self) -> None:
        self._services = SimpleNamespace(dq_report_service=object())
        self._context = SimpleNamespace(run_id="run-1")
        self._config = SimpleNamespace(
            dq_config=_DQConfig(
                soft_fail_threshold=0.11,
                hard_fail_threshold=0.22,
                key_nullability_rules=[_Rule("entity_id", "primary", False)],
            ),
            table_config=_TableConfig(),
            entity_type="publication",
            pipeline_name="pubmed_publication",
            provider="pubmed",
            bronze_output_path="bronze/path",
            silver_output_path="silver/path",
            gold_output_path="gold/path",
            flat_structure=False,
        )
        self._logger = _LoggerStub()
        self._bronze_records_for_dq: list[bytes] = []
        self._silver_records_for_dq: list[dict[str, object]] = []
        self._gold_records_for_dq: list[dict[str, object]] = []
        self._source_batch_ids: list[str] = ["batch-1"]
        self._last_bronze_path: str | None = None
        self._dq_total_seen = 0
        self.records_fetched = 10
        self.records_quarantined = 2


def test_should_collect_dq_data_depends_on_report_service_presence() -> None:
    harness = _BatchExecutorDQHarness()
    assert harness._should_collect_dq_data() is True

    harness._services.dq_report_service = None
    assert harness._should_collect_dq_data() is False


def test_collect_dq_data_skips_unserializable_records_and_tracks_outputs() -> None:
    harness = _BatchExecutorDQHarness()
    bronze_result = SimpleNamespace(path=Path("bronze/file.jsonl"))
    circular_record: dict[str, object] = {}
    circular_record["self"] = circular_record

    harness._collect_dq_data(
        records=[{"ok": 1}, circular_record],
        batch_id=object(),
        bronze_result=bronze_result,
        silver_records=[{"silver": "value"}],
        gold_records=[{"gold": "value"}],
    )

    assert Path(harness._last_bronze_path or "") == Path("bronze/file.jsonl")
    assert len(harness._bronze_records_for_dq) == 1
    assert harness._silver_records_for_dq == [{"silver": "value"}]
    assert harness._gold_records_for_dq == [{"gold": "value"}]


def test_normalize_records_for_polars_stringifies_mixed_nested_columns() -> None:
    records: list[dict[str, object]] = [
        {"payload": {"a": 1}, "id": "1"},
        {"payload": "raw-json", "id": "2"},
    ]

    normalized = _BatchExecutorDQMixin._normalize_records_for_polars(records)

    assert normalized is not None
    assert isinstance(normalized[0]["payload"], str)
    assert isinstance(normalized[1]["payload"], str)


def test_extract_dq_entity_prefers_suffix_from_table_name() -> None:
    harness = _BatchExecutorDQHarness()
    harness._config.table_config.silver_table = "silver_activity"
    assert harness._extract_dq_entity() == "activity"

    harness._config.table_config.silver_table = "domain.activity"
    assert harness._extract_dq_entity() == "activity"

    harness._config.table_config.silver_table = None
    assert harness._extract_dq_entity() == "publication"


def test_get_dq_thresholds_uses_defaults_when_dq_config_missing() -> None:
    harness = _BatchExecutorDQHarness()
    harness._config.dq_config = None

    assert harness._get_dq_thresholds() == (0.05, 0.20)


def test_get_dq_context_builds_context_with_resolved_rules() -> None:
    harness = _BatchExecutorDQHarness()
    harness._bronze_records_for_dq = [b'{"id":1}']
    harness._silver_records_for_dq = [{"entity_id": "A1"}]
    harness._gold_records_for_dq = [{"entity_id": "A1", "score": 0.9}]
    harness._last_bronze_path = "bronze/file.jsonl"
    harness._build_dataframe_from_records = lambda records: {"rows": len(records)}  # type: ignore[method-assign]

    context = harness.get_dq_context()

    assert context is not None
    assert context.run_id == "run-1"
    assert context.entity == "publication"
    assert context.silver_primary_keys == ["entity_id"]
    assert context.dq_soft_threshold == 0.11
    assert context.dq_hard_threshold == 0.22
    assert context.silver_key_nullability_rules == [
        {"field": "entity_id", "key_type": "primary", "nullable": False}
    ]


def test_reservoir_add_respects_max_sample_size(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _BatchExecutorDQHarness()
    monkeypatch.setattr(dq_mixin_module, "_DQ_MAX_SAMPLE_SIZE", 3)

    reservoir: list[int] = []
    for i in range(20):
        harness._reservoir_add(reservoir, i)

    assert len(reservoir) == 3


def test_get_dq_context_returns_none_when_collection_disabled() -> None:
    harness = _BatchExecutorDQHarness()
    harness._services.dq_report_service = None

    assert harness.get_dq_context() is None
