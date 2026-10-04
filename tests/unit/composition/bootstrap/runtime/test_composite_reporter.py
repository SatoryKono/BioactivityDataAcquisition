"""Composite report wiring preserves configured persistence and archive roots."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import bioetl.composition.bootstrap.runtime.composite_reporter as reporter_module
from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineRunResult,
    RunResult,
)
from bioetl.domain.ports import LoggerPort

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("archive_root", [None, "custom-archive"])
def test_composite_reporter_uses_configured_roots_for_capture_and_archive(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, archive_root: str | None
) -> None:
    settings = SimpleNamespace(
        data_dir="custom-data", archive_root=archive_root, report_root=tmp_path
    )
    capture = MagicMock()
    capture_factory = MagicMock(return_value=capture)
    archive = MagicMock()
    monkeypatch.setattr(reporter_module, "get_settings", lambda: settings)
    monkeypatch.setattr(reporter_module, "create_run_status_capture", capture_factory)
    monkeypatch.setattr(reporter_module, "archive_successful_run", archive)
    logger = MagicMock(spec=LoggerPort)

    service = reporter_module.create_composite_reporter(
        pipeline_name="composite_assay", manifest_id="manifest-id", logger=logger
    )

    expected_archive_root = Path(archive_root) if archive_root is not None else None
    assert service.pipeline_name == "composite_assay"
    assert service.manifest_id == "manifest-id"
    assert service.root == tmp_path
    assert service.logger is logger
    assert service.capture is capture
    capture_factory.assert_called_once_with(
        "custom-data", report_root=tmp_path, archive_root=expected_archive_root
    )
    result = RunResult(
        PipelineRunResult.SUCCESS, "composite_assay", "parent-id", "composite"
    )
    assert service.archive is not None
    service.archive(result)
    archive.assert_called_once_with(
        result=result,
        options=None,
        data_root=Path("custom-data"),
        archive_root=expected_archive_root,
        report_root=tmp_path,
    )
