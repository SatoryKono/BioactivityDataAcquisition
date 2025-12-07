"""Integration tests for ChEMBL Activity pipeline (TS-001)."""

from functools import partial
from pathlib import Path
import sys
from unittest.mock import MagicMock

import pandas as pd
import pytest

from bioetl.application.config.runtime import build_runtime_config
from bioetl.application.pipelines.registry import get_pipeline_class
from bioetl.infrastructure.clients.chembl import ChemblExtractionClientImpl
from bioetl.infrastructure.clients.provider_registry_loader import (
    create_provider_loader,
)
from bioetl.interfaces.wiring import build_default_container, create_config_loader

sys.modules.setdefault("tqdm", MagicMock())


@pytest.mark.integration
def test_chembl_activity_pipeline_smoke(tmp_path, monkeypatch):
    """TS-001: full pipeline run writes data and metadata."""
    monkeypatch.setenv(
        "BIOETL_CONFIG_DIR",
        str(Path("tests/fixtures/configs").resolve()),
    )
    monkeypatch.setattr(
        ChemblExtractionClientImpl,
        "get_release_version",
        lambda self: "chembl_integration",
    )

    config_loader = create_config_loader()
    config = build_runtime_config(
        config_path=Path("tests/fixtures/configs/chembl_activity_test.yaml"),
        configs_root=Path("tests/fixtures/configs"),
        loader=config_loader,
    )
    config.storage.output_path = str(tmp_path / "output")

    provider_loader_factory = partial(create_provider_loader)
    registry = provider_loader_factory().get_registry()
    container = build_default_container(
        config,
        provider_registry=registry,
    )
    logger = container.get_logger()
    extraction_service = container.get_extraction_service()
    record_source = container.get_record_source(extraction_service, logger=logger)
    pipeline_cls = get_pipeline_class("activity_chembl")
    pipeline = pipeline_cls(
        config=config,
        logger=logger,
        validation_service=container.get_validation_service(),
        output_writer=container.get_output_writer(),
        extraction_service=extraction_service,
        hash_service=container.get_hash_service(),
        metadata_builder=container.get_metadata_builder(),
        file_record_source_factory=container.get_record_source_factory(),
        record_source=record_source,
        normalization_service=container.get_normalization_service(),
        hooks=container.get_hooks(),
        error_policy=container.get_error_policy(),
    )

    result = pipeline.run(
        output_path=Path(config.storage.output_path),
        dry_run=False,
    )

    output_file = Path(config.storage.output_path) / "activity.csv"
    meta_file = Path(config.storage.output_path) / "meta.yaml"

    assert result.success is True
    assert output_file.exists(), "Pipeline should write output file"
    assert meta_file.exists(), "Pipeline should write metadata"

    df = pd.read_csv(output_file)
    assert len(df) == 2
    assert set(df["activity_id"].tolist()) == {1, 2}
