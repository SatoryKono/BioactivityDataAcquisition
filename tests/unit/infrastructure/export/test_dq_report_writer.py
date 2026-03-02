from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bioetl.application.services.dq.bronze_analyzer import BronzeDQAnalyzer
from bioetl.domain.value_objects.dq_report import BronzeDQReport, DQReportFormat
from bioetl.infrastructure.export.dq_report_writer import DQReportWriter
from bioetl.infrastructure.schemas.dq_report_config import BronzeDQReportConfig


def _build_bronze_report() -> BronzeDQReport:
    analyzer = BronzeDQAnalyzer()
    config = BronzeDQReportConfig(
        enabled=True,
        format="json",
        checks=["record_count", "file_integrity", "schema_snapshot"],
    )
    return analyzer.analyze(
        records=iter([b'{"id": 1}', b'{"id": 2}']),
        run_id="run-1",
        pipeline="chembl_target",
        batch_id="batch-1",
        source_file="chembl/target/2026-03-02/batch_1.jsonl.zst",
        config=config,
        timestamp=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_write_bronze_report_treats_output_path_as_directory(
    tmp_path: Path,
) -> None:
    writer = DQReportWriter(base_path=tmp_path, logger=MagicMock())
    report = _build_bronze_report()
    output_dir = tmp_path / "data" / "output" / "bronze" / "chembl" / "target"

    assert not output_dir.exists()

    report_path = await writer.write_bronze_report(
        report=report,
        output_path=output_dir,
        format=DQReportFormat.JSON,
        provider="chembl",
        entity="target",
    )

    assert output_dir.is_dir()
    assert report_path == output_dir / "bronze_chembl_target_dq_report.json"
    assert report_path.exists()
