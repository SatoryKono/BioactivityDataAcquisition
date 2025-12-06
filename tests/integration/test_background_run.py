"""Smoke-тест фонового запуска пайплайна."""

from pathlib import Path

import pytest

from bioetl.application.config_loader import load_pipeline_config_from_path
from bioetl.application.orchestrator import PipelineOrchestrator
from bioetl.infrastructure.clients.provider_registry_loader import (
    load_provider_registry,
)


@pytest.mark.integration
def test_run_in_background_dry_run(tmp_path):
    config_path = Path("tests/fixtures/configs/chembl_activity_test.yaml")
    config = load_pipeline_config_from_path(
        config_path,
        profile="default",
        profiles_root=Path("tests/fixtures/configs"),
    )

    payload = config.model_dump()
    payload["output_path"] = str(tmp_path / "out")
    payload["input_path"] = str(
        Path("tests/fixtures/input/chembl_activity_small.csv").resolve()
    )
    config_copy = config.__class__(**payload)

    registry = load_provider_registry()
    orchestrator = PipelineOrchestrator(
        "activity_chembl", config_copy, provider_registry=registry
    )

    future = orchestrator.run_in_background(dry_run=True, limit=5)
    result = future.result()

    assert result.success
    assert result.row_count >= 0
    assert not (Path(payload["output_path"]) / "activity.csv").exists()
