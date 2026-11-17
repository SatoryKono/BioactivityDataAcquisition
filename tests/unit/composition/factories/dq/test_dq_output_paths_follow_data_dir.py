"""Bronze/Silver/Gold DQ directories follow ``BIOETL_DATA_DIR`` in test mode."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.application.services.dq.bronze_analyzer import BronzeDQAnalyzer
from bioetl.composition.factories.dq.context_resolver import extract_dq_output_paths
from bioetl.composition.factories.pipeline import _runner_assembly_support as assembly
from bioetl.domain.value_objects.dq_report import DQReportFormat
from bioetl.infrastructure.export.dq_report_writer import DQReportWriter
from bioetl.infrastructure.schemas.dq_report_config import BronzeDQReportConfig

_CWD_BRONZE_REPORT = (
    Path.cwd()
    / "data"
    / "output"
    / "bronze"
    / "chembl"
    / "activity"
    / "bronze_chembl_activity_dq_report.json"
)


def _layer(path: str) -> SimpleNamespace:
    return SimpleNamespace(path=path, flat_structure=False)


def _yaml_config(
    *,
    bronze: str = "data/output/bronze/chembl/activity",
    silver: str = "data/output/silver/chembl/activity",
    gold: str = "data/output/gold/chembl/activity",
) -> SimpleNamespace:
    return SimpleNamespace(
        sink={
            "bronze": _layer(bronze),
            "silver": _layer(silver),
            "gold": _layer(gold),
        }
    )


def _settings(data_dir: Path) -> SimpleNamespace:
    return SimpleNamespace(
        data_dir=data_dir,
        test_mode=True,
        bronze_path=data_dir / "output" / "bronze",
        silver_path=data_dir / "output" / "silver",
        gold_path=data_dir / "output" / "gold",
    )


@pytest.mark.unit
def test_canonical_dq_paths_stay_relative_when_data_dir_is_default() -> None:
    paths = extract_dq_output_paths(_yaml_config(), settings=_settings(Path("data")))

    assert paths.bronze_path == "data/output/bronze/chembl/activity"
    assert paths.silver_path == "data/output/silver/chembl/activity"
    assert paths.gold_path == "data/output/gold/chembl/activity"


@pytest.mark.unit
def test_noncanonical_dq_path_is_left_unchanged(tmp_path: Path) -> None:
    paths = extract_dq_output_paths(
        _yaml_config(
            bronze="custom/bronze",
            silver="custom/silver",
            gold="custom/gold",
        ),
        settings=_settings(tmp_path / "runtime_data"),
    )

    assert paths.bronze_path == "custom/bronze"
    assert paths.silver_path == "custom/silver"
    assert paths.gold_path == "custom/gold"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_test_mode_bronze_dq_report_is_written_under_data_dir(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "runtime_data"
    existed_before = _CWD_BRONZE_REPORT.exists()

    paths = extract_dq_output_paths(_yaml_config(), settings=_settings(data_dir))
    report_dir = Path(str(paths.bronze_path))
    analyzer = BronzeDQAnalyzer()
    report = analyzer.analyze(
        records=iter([b'{"id": 1}']),
        run_id="run-1",
        pipeline="chembl_activity",
        batch_id="batch-1",
        source_file="cached",
        config=BronzeDQReportConfig(enabled=True, format="json"),
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
    )
    writer = DQReportWriter(base_path=tmp_path / "unused-fallback", logger=MagicMock())
    try:
        written = await writer.write_bronze_report(
            report=report,
            output_path=report_dir,
            report_format=DQReportFormat.JSON,
            provider="chembl",
            entity="activity",
        )
        expected = (
            data_dir
            / "output"
            / "bronze"
            / "chembl"
            / "activity"
            / "bronze_chembl_activity_dq_report.json"
        )
        assert written == expected
        assert expected.is_file()
        assert paths.silver_path == str(
            data_dir / "output" / "silver" / "chembl" / "activity"
        )
        assert paths.gold_path == str(
            data_dir / "output" / "gold" / "chembl" / "activity"
        )
        assert _CWD_BRONZE_REPORT.exists() is existed_before
    finally:
        if _CWD_BRONZE_REPORT.exists() and not existed_before:
            _CWD_BRONZE_REPORT.unlink()


@pytest.mark.unit
def test_batch_executor_uses_assembly_settings_not_global_data_dir(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    job_dir = tmp_path / "job"
    global_dir = tmp_path / "global"
    captured: dict[str, object] = {}

    def _capture(request: Any) -> str:
        captured["bronze"] = request.bronze_output_path
        return "executor"

    monkeypatch.setattr(
        assembly.ServicesBuilder,
        "create_batch_executor_from_pipeline",
        staticmethod(_capture),
    )
    monkeypatch.setattr(assembly, "extract_pipeline_callbacks", lambda _pipeline: None)
    monkeypatch.setattr(
        "bioetl.composition.runtime_builders.config_access.get_settings",
        lambda: _settings(global_dir),
    )
    context = MagicMock()
    context.yaml_config = _yaml_config()
    context.settings = _settings(job_dir)

    result = assembly.build_batch_executor(
        context,
        checkpoint_manager=MagicMock(),
        lock_runtime_service=MagicMock(),
        observer=MagicMock(),
    )

    assert result == "executor"
    assert captured["bronze"] == str(
        job_dir / "output" / "bronze" / "chembl" / "activity"
    )
