"""Интеграционный тест UnifiedOutputWriter с реальными зависимостями."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest
import yaml

from bioetl.application.config.pipeline_config_schema import DeterminismConfig, QcConfig
from bioetl.domain.models import RunContext
from bioetl.infrastructure.files.atomic import AtomicFileOperation
from bioetl.infrastructure.output.impl.csv_writer import CsvWriterImpl
from bioetl.infrastructure.output.impl.metadata_writer import MetadataWriterImpl
from bioetl.infrastructure.output.impl.quality_report import QualityReportImpl
from bioetl.infrastructure.output.unified_writer import UnifiedOutputWriter


@pytest.mark.integration
def test_unified_writer_writes_data_and_meta(tmp_path):
    df = pd.DataFrame({"value": [3, 1, 2], "id": [2, 3, 1]})
    config = DeterminismConfig(stable_sort=True)
    qc_config = QcConfig(enable_quality_report=True, enable_correlation_report=True)
    writer = CsvWriterImpl()
    metadata_writer = MetadataWriterImpl()
    quality_reporter = QualityReportImpl()
    atomic_op, calls = _with_tracking_atomic()

    run_context = RunContext(
        run_id="test-run",
        entity_name="test_entity",
        provider="chembl",
        started_at=datetime.now(timezone.utc),
        config={"hashing": {"business_key_fields": ["id"]}},
    )

    unified_writer = UnifiedOutputWriter(
        writer,
        metadata_writer,
        quality_reporter,
        config,
        qc_config=qc_config,
        atomic_op=atomic_op,
    )

    output_dir = tmp_path / "out"
    result = unified_writer.write_result(df, output_dir, "test_entity", run_context)

    data_path = output_dir / "test_entity.csv"
    meta_path = output_dir / "meta.yaml"

    _assert_write_results(calls, result, data_path, meta_path, run_context)


def _with_tracking_atomic() -> tuple[AtomicFileOperation, dict[str, int]]:
    atomic_op = AtomicFileOperation()
    calls = {"count": 0}
    original_write_atomic = atomic_op.write_atomic

    def tracking_write_atomic(path: Path, write_fn):
        calls["count"] += 1
        return original_write_atomic(path, write_fn)

    atomic_op.write_atomic = tracking_write_atomic  # type: ignore[assignment]
    return atomic_op, calls


def _assert_write_results(
    calls: dict[str, int],
    result,
    data_path: Path,
    meta_path: Path,
    run_context: RunContext,
) -> None:
    _assert_atomic_calls(calls)
    _assert_written_artifacts(data_path, meta_path)
    _assert_written_data(data_path)
    _assert_written_meta(meta_path, run_context)
    assert result.row_count == 3
    assert result.checksum is not None


def _assert_atomic_calls(calls: dict[str, int]) -> None:
    assert calls["count"] == 3


def _assert_written_artifacts(data_path: Path, meta_path: Path) -> None:
    assert data_path.exists()
    assert meta_path.exists()


def _assert_written_data(data_path: Path) -> None:
    written = pd.read_csv(data_path)
    assert list(written.columns) == ["id", "value"]
    assert written["id"].tolist() == [1, 2, 3]
    assert written["value"].tolist() == [2, 3, 1]


def _assert_written_meta(meta_path: Path, run_context: RunContext) -> None:
    meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    assert meta["run_id"] == run_context.run_id
    assert "hash" in meta
    assert "quality_report_table.csv" in meta["files"]
    assert "correlation_report_table.csv" in meta["files"]

