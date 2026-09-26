# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for BatchExecutor DQ helper mixin."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
import sys

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


class _MetricsStub:
    def __init__(self) -> None:
        self.increment_calls: list[tuple[str, int, dict[str, str]]] = []

    def increment_counter(
        self,
        name: str,
        value: int,
        labels: dict[str, str] | None = None,
        **_: object,
    ) -> None:
        self.increment_calls.append((name, value, labels or {}))


class _BatchExecutorDQHarness(_BatchExecutorDQMixin):
    def __init__(self) -> None:
        self._services = SimpleNamespace(  # type: ignore[assignment]
            dq_report_service=object(),
            metrics=_MetricsStub(),
        )
        self._context = SimpleNamespace(  # type: ignore[assignment]
            run_id="run-1",
            started_at=datetime(2026, 4, 9, 12, 30, 0, tzinfo=UTC),
            replay_timestamp_anchor=None,
        )
        self._config = SimpleNamespace(  # type: ignore[assignment]
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
            scd_config=None,
        )
        self._logger = _LoggerStub()  # type: ignore[assignment]
        self._bronze_records_for_dq: list[bytes] = []
        self._silver_records_for_dq: list[dict[str, object]] = []
        self._gold_records_for_dq: list[dict[str, object]] = []
        self.source_batch_ids: list[str] = ["batch-1"]
        self._last_bronze_path: str | None = None
        self._dq_total_seen = 0
        self._dq_reservoir_ranks: dict[int, list[str]] = {}
        self.records_fetched = 10
        self.records_quarantined = 2


def test_should_collect_dq_data_depends_on_report_service_presence() -> None:
    harness = _BatchExecutorDQHarness()
    assert harness._should_collect_dq_data() is True

    harness._services.dq_report_service = None  # type: ignore[misc]
    assert harness._should_collect_dq_data() is False


def test_collect_dq_data_skips_unserializable_records_and_tracks_outputs() -> None:
    harness = _BatchExecutorDQHarness()
    bronze_result = SimpleNamespace(path=Path("bronze/file.jsonl"))
    circular_record: dict[str, object] = {}
    circular_record["self"] = circular_record

    harness._collect_dq_data(
        records=[{"ok": 1}, circular_record],
        batch_id=object(),  # type: ignore[arg-type]
        bronze_result=bronze_result,
        silver_records=[{"silver": "value"}],
        gold_records=[{"gold": "value"}],
    )

    assert Path(harness._last_bronze_path or "") == Path("bronze/file.jsonl")
    assert len(harness._bronze_records_for_dq) == 1
    assert harness._bronze_records_for_dq[0] == b'{"ok":1}'
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


def test_build_dataframe_from_records_handles_null_then_string_columns() -> None:
    try:
        import polars as pl
    except ImportError:
        pytest.skip("polars not installed")

    harness = _BatchExecutorDQHarness()
    records: list[dict[str, object]] = [
        {"entity_id": "1", "assay_test_type": None} for _ in range(150)
    ]
    records.append({"entity_id": "151", "assay_test_type": "In vitro"})

    df = harness._build_dataframe_from_records(records)

    assert df is not None
    assert isinstance(df, pl.DataFrame)
    assert df.shape == (151, 2)
    assert df["assay_test_type"].to_list()[-1] == "In vitro"
    assert harness._logger.warning_calls == []
    assert harness._services.metrics.increment_calls == []


def test_build_dataframe_from_records_emits_metric_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _BatchExecutorDQHarness()
    records: list[dict[str, object]] = [
        {"entity_id": "1", "payload": "value"},
    ]

    def _raise_dataframe_error(*args: object, **kwargs: object) -> object:
        raise RuntimeError("boom")

    fake_polars = SimpleNamespace(
        DataFrame=_raise_dataframe_error,
        exceptions=SimpleNamespace(PolarsError=RuntimeError),
    )
    monkeypatch.setitem(sys.modules, "polars", fake_polars)

    df = harness._build_dataframe_from_records(records, stage="silver")

    assert df is None
    assert harness._logger.warning_calls
    assert harness._services.metrics.increment_calls == [
        (
            "bioetl_dq_context_build_failures_total",
            1,
            {
                "pipeline": "pubmed_publication",
                "stage": "silver",
                "reason": "dq_dataframe_build_failed",
            },
        )
    ]


def test_extract_dq_entity_prefers_suffix_from_table_name() -> None:
    harness = _BatchExecutorDQHarness()
    harness._config.table_config.silver_table = "silver_activity"  # type: ignore[misc]
    assert harness._extract_dq_entity() == "activity"

    harness._config.table_config.silver_table = "domain.activity"  # type: ignore[misc]
    assert harness._extract_dq_entity() == "activity"

    harness._config.table_config.silver_table = None  # type: ignore[misc]
    assert harness._extract_dq_entity() == "publication"


def test_get_dq_thresholds_uses_defaults_when_dq_config_missing() -> None:
    harness = _BatchExecutorDQHarness()
    harness._config.dq_config = None  # type: ignore[misc]

    assert harness._get_dq_thresholds() == (0.05, 0.20)


def test_get_dq_context_builds_context_with_resolved_rules() -> None:
    harness = _BatchExecutorDQHarness()
    harness._bronze_records_for_dq = [b'{"id":1}']
    harness._silver_records_for_dq = [{"entity_id": "A1"}]
    harness._gold_records_for_dq = [{"entity_id": "A1", "score": 0.9}]
    harness._last_bronze_path = "bronze/file.jsonl"
    harness._build_dataframe_from_records = (  # type: ignore[method-assign]
        lambda records, stage="other": {"rows": len(records)}
    )

    context = harness.get_dq_context()

    assert context is not None
    assert context.run_id == "run-1"
    assert context.entity == "publication"
    assert context.silver_primary_keys == ["entity_id"]
    assert context.dq_soft_threshold == pytest.approx(0.11)
    assert context.dq_hard_threshold == pytest.approx(0.22)
    assert context.silver_key_nullability_rules == [
        {"field": "entity_id", "key_type": "primary", "nullable": False}
    ]
    assert context.timestamp == harness._context.started_at
    assert context.bronze_date_str == "2026-04-09"


def test_get_dq_context_prefers_replay_timestamp_anchor_for_exact_replay() -> None:
    harness = _BatchExecutorDQHarness()
    harness._context.replay_timestamp_anchor = datetime(
        2026,
        4,
        10,
        0,
        0,
        0,
        tzinfo=UTC,
    )
    harness._build_dataframe_from_records = (  # type: ignore[method-assign]
        lambda records, stage="other": {"rows": len(records)}
    )

    context = harness.get_dq_context()

    assert context is not None
    assert context.timestamp == harness._context.replay_timestamp_anchor
    assert context.bronze_date_str == "2026-04-10"


def test_reservoir_add_respects_max_sample_size(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _BatchExecutorDQHarness()
    monkeypatch.setattr(dq_mixin_module, "_DQ_MAX_SAMPLE_SIZE", 3)

    reservoir: list[int] = []
    for i in range(20):
        harness._reservoir_add("bronze", reservoir, i)

    assert len(reservoir) == 3


def test_reservoir_add_is_order_independent_for_same_items(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dq_mixin_module, "_DQ_MAX_SAMPLE_SIZE", 3)
    first_harness = _BatchExecutorDQHarness()
    second_harness = _BatchExecutorDQHarness()

    first_reservoir: list[dict[str, object]] = []
    second_reservoir: list[dict[str, object]] = []
    records = [
        {"id": "4", "payload": "d"},
        {"id": "2", "payload": "b"},
        {"id": "1", "payload": "a"},
        {"id": "5", "payload": "e"},
        {"id": "3", "payload": "c"},
    ]

    for record in records:
        first_harness._reservoir_add("silver", first_reservoir, record)
    for record in reversed(records):
        second_harness._reservoir_add("silver", second_reservoir, record)

    def normalize(items):
        return sorted(
            _BatchExecutorDQMixin._serialize_dq_sample_item(item) for item in items
        )

    assert normalize(first_reservoir) == normalize(second_reservoir)


def test_get_dq_context_returns_none_when_collection_disabled() -> None:
    harness = _BatchExecutorDQHarness()
    harness._services.dq_report_service = None  # type: ignore[misc]

    assert harness.get_dq_context() is None
