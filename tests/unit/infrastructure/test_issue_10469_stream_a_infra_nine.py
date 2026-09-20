"""Stream A infra leftovers without gold_writer/silver_writer/deltalake."""

from __future__ import annotations

import errno
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import zstandard as zstd

from bioetl.domain.workflow.foreign_key_reconciliation import (
    ForeignKeyReconciliationRequest,
)
from bioetl.infrastructure.adapters.crossref.fetch_flow import CrossRefFetchFlow
from bioetl.infrastructure.observability.anomaly.detector import AnomalyDetector
from bioetl.infrastructure.observability.prometheus_metrics import (
    PrometheusMetrics,
    _CounterMetric,
    _CounterObserver,
    _has_declared_labels,
    _HistogramMetric,
    _HistogramObserver,
    _reject_unexpected_labels,
)
from bioetl.infrastructure.quarantine import _pyarrow_helpers as pyarrow_helpers
from bioetl.infrastructure.storage.bronze.read_cleanup_mixin import (
    BronzeWriterReadCleanupMixin,
)
from bioetl.infrastructure.storage.delta.resilience import AdaptiveRetryPolicy
from bioetl.infrastructure.storage.support._atomic_replace import (
    AtomicWriteError,
    _confined_replace_pair,
    _is_retryable_replace_error,
    _replace_prevalidated_with_retry,
    _replace_with_retry,
    _retry_delay_or_raise,
)
from bioetl.infrastructure.storage.support.atomic_group import AtomicWriteGroup
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_quarantine_keys import (
    resolve_mutation_identity_keys,
)
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_support import (
    filter_source_rows_to_current_run,
    normalize_row_key,
    normalize_value,
    partition_source_rows,
    record_reconciliation_metrics,
)

pytestmark = pytest.mark.unit


def _fk_request(**overrides: object) -> ForeignKeyReconciliationRequest:
    payload: dict[str, object] = {
        "source_table": "src",
        "reference_table": "ref",
        "source_key": "parent_id",
        "reference_key": "id",
        "primary_keys": ("id",),
    }
    payload.update(overrides)
    return ForeignKeyReconciliationRequest(**payload)


def test_atomic_replace_retry_and_confinement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "out.txt"
    other = tmp_path / "nested"
    other.mkdir()
    temp = tmp_path / ".tmp"
    temp.write_text("x", encoding="utf-8")
    with pytest.raises(AtomicWriteError, match="temp path parent"):
        _confined_replace_pair(other / "tmp", target)

    locked = OSError("busy")
    locked.winerror = 5
    assert _is_retryable_replace_error(locked) is True
    errno_locked = OSError(errno.EBUSY, "busy")
    errno_locked.errno = 16
    assert _is_retryable_replace_error(errno_locked) is True

    policy = AdaptiveRetryPolicy(
        enabled=True,
        max_retries=2,
        base_delay_seconds=0.0,
        max_delay_seconds=0.0,
        jitter_seconds=0.0,
        adaptive=False,
    )
    assert _retry_delay_or_raise(locked, retry_policy=policy, retry_count=0) == 0.0
    attempts = {"n": 0}

    def _flaky_replace(self: Path, dest: Path) -> Path:
        attempts["n"] += 1
        if attempts["n"] == 1:
            error = OSError("sharing")
            error.winerror = 32
            error.errno = 16
            raise error
        dest.write_text("ok", encoding="utf-8")
        return dest

    monkeypatch.setattr(Path, "replace", _flaky_replace)
    retries: list[int] = []
    _replace_prevalidated_with_retry(
        temp,
        target,
        retry_policy=policy,
        on_retry=lambda attempt, _delay, _error: retries.append(attempt),
    )
    assert retries == [1]
    _replace_with_retry(temp, target, retry_policy=policy)


def test_atomic_group_add_cleans_temp_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    group = AtomicWriteGroup()

    def _boom(_temp: Path, _target: Path) -> tuple[Path, Path]:
        raise ValueError("parent mismatch")

    monkeypatch.setattr(
        "bioetl.infrastructure.storage.support.atomic_group._confined_replace_pair",
        _boom,
    )
    with pytest.raises(ValueError, match="parent mismatch"):
        group.add(tmp_path / "out.json", b"payload")


def test_prometheus_unlabeled_metric_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    _HistogramObserver.observe(object(), 1.5)
    _CounterObserver.inc(object(), 2.0)
    _HistogramMetric.observe(object(), 3.0)
    _CounterMetric.inc(object(), 4.0)
    assert _has_declared_labels(SimpleNamespace(_labelnames=())) is False
    assert _has_declared_labels(SimpleNamespace()) is None
    with pytest.raises(ValueError, match="does not accept labels"):
        _reject_unexpected_labels("metric", {"a": "1"})
    _reject_unexpected_labels("metric", {})

    unlabeled = SimpleNamespace(
        _labelnames=(),
        observe=MagicMock(),
        inc=MagicMock(),
        set=MagicMock(),
    )
    metrics = PrometheusMetrics()
    monkeypatch.setattr(
        "bioetl.infrastructure.observability.prometheus_metrics._require_registered_metric",
        lambda **_kwargs: unlabeled,
    )
    metrics.observe_histogram("h", 1.0, None)
    metrics.increment_counter("c", 1, None)
    metrics.set_gauge("g", 1.0, None)
    unlabeled.observe.assert_called_once()
    unlabeled.inc.assert_called_once()
    unlabeled.set.assert_called_once()


async def test_bronze_read_list_cleanup_and_preview(tmp_path: Path) -> None:
    payload = b'{"a": 1}\n\n{"b": 2}\n'
    compressed = zstd.ZstdCompressor().compress(payload)
    batch_dir = tmp_path / "chembl" / "activity" / "2024-01-01"
    batch_dir.mkdir(parents=True)
    batch_path = batch_dir / "batch_001.jsonl.zst"
    batch_path.write_bytes(compressed)
    nested_dir = batch_dir / "nested"
    nested_dir.mkdir()
    host = BronzeWriterReadCleanupMixin()
    host.base_path = tmp_path
    host._flat_structure = False
    host._logger = MagicMock()
    host._metrics = MagicMock()
    rows = [
        row
        async for row in host.read_bronze(
            "chembl/activity/2024-01-01/batch_001.jsonl.zst"
        )
    ]
    assert rows == [{"a": 1}, {"b": 2}]
    listed = await host.list_batches(
        "chembl", "activity", datetime(2024, 1, 1, tzinfo=UTC)
    )
    assert listed
    assert host._list_batches_sync("", "", None) == []
    host._flat_structure = True
    assert host._list_batches_sync("", "", datetime(2099, 1, 1, tzinfo=UTC)) == []
    dated = tmp_path / "2024-01-02"
    dated.mkdir()
    (dated / "batch_001.jsonl.zst").write_bytes(b"x")
    assert host._list_batches_sync("", "", datetime(2024, 1, 2, tzinfo=UTC))
    host._flat_structure = False
    missing = BronzeWriterReadCleanupMixin()
    missing.base_path = tmp_path / "gone"
    missing._flat_structure = False
    missing._logger = MagicMock()
    missing._metrics = MagicMock()
    assert missing._find_old_date_dirs("2021-01-01") == []
    (tmp_path / "pubchem").mkdir()
    (tmp_path / "pubchem" / "compound").write_bytes(b"not-a-dir")
    assert host._find_old_date_dirs("2021-01-01", "pubchem", "compound") == []
    cleaned = await host.cleanup_old_files(
        datetime(2099, 1, 1, tzinfo=UTC),
        dry_run=False,
        provider="chembl",
        entity="activity",
    )
    assert cleaned["files_removed"] >= 1
    host._metrics.increment_counter.assert_called()
    preview = host.preview_cleanup(provider="chembl", entity="activity")
    assert "path" in preview
    host._flat_structure = True
    assert host.preview_cleanup()["exists"] is True
    host._flat_structure = False
    assert host._resolve_bronze_preview_root("chembl", None).name == "chembl"
    assert host._resolve_bronze_preview_root(None, None) == tmp_path


async def test_crossref_fetch_flow_honors_limit() -> None:
    async def _fetch_batch(batch: list[str]):
        for item in batch:
            yield {"doi": item}
            yield {"doi": f"{item}-extra"}

    mapper = SimpleNamespace(
        with_lookup_method=lambda publication, _method: publication
    )

    async def _execute(**kwargs: object):
        fetcher = kwargs["primary_record_fetcher"]
        async for row in fetcher(["a", "b", "c"], kwargs["limit"]):
            yield row

    flow = CrossRefFetchFlow(
        logger=MagicMock(),
        batch_fetcher=SimpleNamespace(fetch_batch=_fetch_batch),  # type: ignore[arg-type]
        search_paginator=MagicMock(),  # type: ignore[arg-type]
        fallback_decorator=SimpleNamespace(execute=_execute),  # type: ignore[arg-type]
        batch_size=1,
        response_mapper=mapper,  # type: ignore[arg-type]
    )
    filtered = [
        row
        async for row in flow.fetch_filtered(
            entity_type="publication",
            filter_ids=["a", "b", "c"],
            filter_field="title",
            limit=2,
        )
    ]
    assert len(filtered) == 2
    none = [
        row
        async for row in flow.fetch_filtered_with_fallback(
            entity_type="publication",
            filter_ids=["a", "b"],
            filter_field="doi",
            fallback_mapping={},
            limit=0,
        )
    ]
    assert none == []
    fallback_rows = [
        row
        async for row in flow.fetch_filtered_with_fallback(
            entity_type="publication",
            filter_ids=["a", "b", "c"],
            filter_field="doi",
            fallback_mapping={},
            limit=2,
        )
    ]
    assert len(fallback_rows) == 2


def test_fk_support_leftovers(monkeypatch: pytest.MonkeyPatch) -> None:
    empty, disposition = filter_source_rows_to_current_run(
        [], source_scope="current_run", source_run_ids=("run-a",)
    )
    assert empty == []
    assert disposition == "current_run"
    assert normalize_value(1.25) == ("float", 1.25)

    class _Blank:
        def __str__(self) -> str:
            return "  "

    class _Named:
        def __str__(self) -> str:
            return "token"

    assert normalize_value(_Blank()) is None
    other = normalize_value(_Named())
    assert other is not None and other[0] == "other"
    assert (
        normalize_row_key({"parent_id": None}, ("parent_id",), nulls_equal=True)
        is not None
    )
    record_reconciliation_metrics(
        SimpleNamespace(increment_counter="not-callable"),
        scanned=1,
        retained=1,
        deleted=0,
        scanned_metric="s",
        retained_metric="r",
        deleted_metric="d",
    )
    monkeypatch.setattr(
        "bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_support.row_has_null_foreign_key",
        lambda *_a, **_k: False,
    )
    monkeypatch.setattr(
        "bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_support.normalize_row_key",
        lambda *_a, **_k: None,
    )
    retained, orphans = partition_source_rows(
        _fk_request(),
        source_rows=[{"id": "1", "parent_id": "x"}],
        reference_values=set(),
    )
    assert orphans == []
    assert retained == [{"id": "1", "parent_id": "x"}]
    mixed = resolve_mutation_identity_keys(
        [{"id": "1", "_run_id": "a"}, {"id": "2"}],
        ("id",),
        source_scope="all_current",
    )
    assert mixed == ("id",)
    with pytest.raises(ValueError, match="blank row identity"):
        resolve_mutation_identity_keys(
            [{"id": "1", "_run_id": " "}],
            ("id",),
            source_scope="current_run",
        )
    skipped = resolve_mutation_identity_keys(
        [{"id": "1", "_run_id": " "}, {"id": "2", "_run_id": " "}],
        ("id",),
        source_scope="all_current",
    )
    assert skipped == ("id",)


def test_anomaly_detector_timestamp_and_one_sided_thresholds() -> None:
    detector = AnomalyDetector(min_baseline_samples=1, baseline_window=3)
    detector.update_baseline("latency", [1.0, 2.0, 3.0])
    assert detector.detect("latency", 99.0, timestamp=None) is None
    detector.set_threshold("cpu", min_value=0.0, max_value=1.0)
    assert detector.detect("cpu", 0.5, timestamp=None) is None
    ts = datetime(2024, 1, 1, tzinfo=UTC)
    detector.set_threshold("only_max", min_value=None, max_value=1.0)
    assert detector.detect("only_max", 5.0, timestamp=ts) is not None
    detector.set_threshold("only_min", min_value=10.0, max_value=None)
    assert detector.detect("only_min", 1.0, timestamp=ts) is not None
    detector.set_threshold("open", min_value=None, max_value=None)
    assert detector.detect("open", 1.0, timestamp=ts) is None


def test_pyarrow_helpers_require_compute(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pyarrow_helpers, "pc", None)
    with pytest.raises(RuntimeError, match="pyarrow.compute"):
        pyarrow_helpers._require_pyarrow_compute()
