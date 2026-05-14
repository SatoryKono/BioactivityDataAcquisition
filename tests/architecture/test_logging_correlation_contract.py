"""Architecture guards for logging correlation contracts."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from bioetl.domain.context import PipelineRunContext
from bioetl.domain.types import RunType

ROOT = Path(__file__).resolve().parents[2]
PIPELINE_RUNNER_SERVICE_PATH = (
    ROOT
    / "src"
    / "bioetl"
    / "application"
    / "services"
    / "execution"
    / "execution/pipeline_runner_service.py"
)


@pytest.mark.architecture
def test_pipeline_run_context_exposes_required_log_correlation_fields() -> None:
    """PipelineRunContext must remain the SSOT for correlation-bound log fields."""
    ctx_without_manifest = PipelineRunContext(
        pipeline_name="chembl_activity",
        run_id=uuid4(),
        run_type=RunType.INCREMENTAL,
    )
    ctx_with_manifest = PipelineRunContext(
        pipeline_name="chembl_activity",
        run_id=uuid4(),
        run_type=RunType.INCREMENTAL,
        manifest_id="manifest-123",
    )

    assert ctx_without_manifest.log_correlation_fields() == {
        "run_id": str(ctx_without_manifest.run_id),
        "pipeline": "chembl_activity",
        "pipeline_name": "chembl_activity",
    }
    assert ctx_with_manifest.log_correlation_fields() == {
        "run_id": str(ctx_with_manifest.run_id),
        "pipeline": "chembl_activity",
        "pipeline_name": "chembl_activity",
        "manifest_id": "manifest-123",
    }


@pytest.mark.architecture
def test_pipeline_runner_service_binds_logger_through_context_contract() -> None:
    """Runner service must source correlation fields from PipelineRunContext."""
    source = PIPELINE_RUNNER_SERVICE_PATH.read_text(encoding="utf-8")

    assert "context.log_correlation_fields()" in source, (
        "PipelineRunnerService must bind its run logger through "
        "PipelineRunContext.log_correlation_fields() so correlation anchors "
        "stay explicit and testable."
    )
    assert "self.logger.bind(**context.log_correlation_fields())" in source, (
        "PipelineRunnerService must pass the explicit correlation contract "
        "directly into LoggerPort.bind()."
    )
