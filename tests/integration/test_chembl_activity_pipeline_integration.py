"""Integration tests for ChEMBL Activity pipeline (TS-001)."""
from pathlib import Path
import sys
from unittest.mock import MagicMock

import pandas as pd
import pytest

sys.modules.setdefault("tqdm", MagicMock())

from bioetl.application.container import build_pipeline_dependencies  # noqa: E402
from bioetl.application.pipelines.registry import get_pipeline_class  # noqa: E402
from bioetl.application.services.chembl_extraction import ChemblExtractionServiceImpl  # noqa: E402
from bioetl.infrastructure.config.resolver import ConfigResolver  # noqa: E402


@pytest.mark.integration
def test_chembl_activity_pipeline_smoke(tmp_path, monkeypatch):
    """TS-001: full pipeline run writes data and metadata."""
    monkeypatch.setenv(
        "BIOETL_CONFIG_DIR",
        str(Path("tests/fixtures/configs").resolve()),
    )
    monkeypatch.setattr(
        ChemblExtractionServiceImpl,
        "get_release_version",
        lambda self: "chembl_integration",
    )

    resolver = ConfigResolver()
    config = resolver.resolve("chembl_activity_test.yaml")
    config.storage.output_path = str(tmp_path / "output")

    container = build_pipeline_dependencies(config)
    pipeline_cls = get_pipeline_class("activity_chembl")
    pipeline = pipeline_cls(
        config=config,
        logger=container.get_logger(),
        validation_service=container.get_validation_service(),
        output_writer=container.get_output_writer(),
        extraction_service=container.get_extraction_service(),
        hash_service=container.get_hash_service(),
    )

    result = pipeline.run(output_path=Path(config.storage.output_path), dry_run=False)

    output_file = Path(config.storage.output_path) / "activity.csv"
    meta_file = Path(config.storage.output_path) / "meta.yaml"

    assert result.success is True
    assert output_file.exists(), "Pipeline should write output file"
    assert meta_file.exists(), "Pipeline should write metadata"

    df = pd.read_csv(output_file)
    assert len(df) == 2
    assert set(df["activity_id"].tolist()) == {1, 2}
