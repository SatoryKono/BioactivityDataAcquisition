# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# PD5 test mock/fixture surface.
"""OBS-LIFE-001 / OBS-PROV-001 / OBS-DQ-001 fixture emission contracts."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bioetl.application.core._batch_processing_metrics_support import (
    track_bronze_write_metrics,
    track_storage_write_metrics,
    track_transform_result_metrics,
)
from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
from bioetl.application.core.batch_transformer_state import TransformResult
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters._health_check_observability import (
    handle_health_check_result,
)
from bioetl.infrastructure.adapters.health_check_contract import HealthCheckContext

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[4]
MANIFEST = (
    ROOT
    / "tests"
    / "fixtures"
    / "observability"
    / "chembl_assay_backfill_metric_manifest.json"
)


def _manifest() -> dict[str, object]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_metric_manifest_matches_assay_accounting_contract() -> None:
    payload = _manifest()
    accounting = payload["accounting"]
    assert payload["pipeline"] == "chembl_assay"
    assert payload["run_type"] == "backfill"
    assert accounting["bronze_records"] == 1000
    assert accounting["silver_valid"] == 1000
    assert accounting["gold_written"] == 983
    assert accounting["gold_excluded_by_contract"] == 17
    assert accounting["quarantined"] == 0
    assert (
        accounting["gold_written"] + accounting["gold_excluded_by_contract"]
        == accounting["silver_valid"]
    )


def test_transform_metrics_expose_seventeen_contract_exclusions() -> None:
    metrics = MagicMock()
    recorder = BatchMetricsRecorderService(
        metrics,
        pipeline_label="chembl_assay",
        run_type_label="backfill",
    )
    result = TransformResult(
        silver_records=[{} for _ in range(1000)],
        gold_records=[{} for _ in range(983)],
        quarantined_count=0,
        gold_excluded_by_contract_count=17,
    )

    track_bronze_write_metrics(recorder, record_count=1000)
    track_transform_result_metrics(recorder, transform_result=result)
    track_storage_write_metrics(recorder, transform_result=result)

    metrics.increment_counter.assert_any_call(
        "bioetl_records_processed_total",
        1000,
        {
            "pipeline": "chembl_assay",
            "stage": "bronze",
            "run_type": "backfill",
        },
    )
    metrics.increment_counter.assert_any_call(
        "bioetl_stage_records_total",
        17,
        {
            "pipeline": "chembl_assay",
            "run_type": "backfill",
            "stage": "gold",
            "outcome": "excluded_by_contract",
        },
    )
    metrics.increment_counter.assert_any_call(
        "bioetl_stage_records_total",
        983,
        {
            "pipeline": "chembl_assay",
            "run_type": "backfill",
            "stage": "gold",
            "outcome": "written",
        },
    )


def test_chembl_health_probe_emits_provider_universe_counter() -> None:
    metrics = MagicMock()
    logger = MagicMock()
    handle_health_check_result(
        logger=logger,
        metrics=metrics,
        ctx=HealthCheckContext(provider="chembl", endpoint="/chembl/api/data/status"),
        status=HealthStatus.HEALTHY,
    )
    metrics.increment_counter.assert_called_once_with(
        "bioetl_health_check_success_total",
        1,
        {"provider": "chembl"},
    )


def test_cached_bronze_health_check_does_not_emit_chembl_counters() -> None:
    source_cls = __import__(
        "bioetl.infrastructure.adapters.cached_bronze_data_source",
        fromlist=["CachedBronzeDataSource"],
    ).CachedBronzeDataSource
    source = object.__new__(source_cls)
    assert "handle_health_check_result" not in source.health_check.__code__.co_names
    assert "bioetl_health_check_success_total" not in (
        source.health_check.__code__.co_consts or ()
    )
