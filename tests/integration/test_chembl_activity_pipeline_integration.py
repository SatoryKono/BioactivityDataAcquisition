"""Integration tests for ChEMBL Activity pipeline (TS-001)."""

from functools import partial
from pathlib import Path
import sys
from unittest.mock import MagicMock

import pandas as pd
import pytest

from bioetl.application.config.runtime import build_runtime_config
from bioetl.application.pipelines.registry import get_pipeline_class
from bioetl.application.services.schema_bootstrap import create_schema_bootstrap_service
from bioetl.application.services.schema_contract_provider import SchemaContractProviderImpl
from bioetl.infrastructure.clients.chembl import ChemblExtractionServiceImpl
from bioetl.infrastructure.config.provider_registry import (
    create_provider_loader,
)
from bioetl.infrastructure.config.loader import (
    get_schema_contract_provider,
    set_schema_contract_provider,
)
from bioetl.interfaces.container_factory import (
    build_default_container,
    create_config_loader,
)

sys.modules.setdefault("tqdm", MagicMock())


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

    # Ensure schema contract provider is initialized
    if get_schema_contract_provider() is None:
        bootstrap = create_schema_bootstrap_service()
        provider = SchemaContractProviderImpl(bootstrap.ensure_registered())
        set_schema_contract_provider(provider)

    config_loader = create_config_loader()
    config = build_runtime_config(
        config_path=Path("tests/fixtures/configs/chembl_activity_test.yaml"),
        configs_root=Path("tests/fixtures/configs"),
        loader=config_loader,
    )
    # Update frozen sink config using model_copy
    output_path_str = str(tmp_path / "output")
    new_sink = config.sink.model_copy(update={"output_path": output_path_str})
    object.__setattr__(config, "sink", new_sink)
    # Also update storage if it exists
    if hasattr(config.runtime, "storage"):
        new_storage = config.runtime.storage.model_copy(
            update={"output_path": output_path_str}
        )
        object.__setattr__(config.runtime, "storage", new_storage)

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
        loader=container.get_loader(),
        extraction_service=extraction_service,
        hash_service=container.get_hash_service(),
        index_generator=container.get_index_generator(),
        timestamp_provider=container.get_timestamp_provider(),
        metadata_builder=container.get_metadata_builder(),
        record_source=record_source,
        normalization_service=container.get_normalization_service(),
        hooks=container.get_hooks(),
        error_policy=container.get_error_policy(),
    )

    output_path = Path(config.sink.output_path)
    result = pipeline.run(
        output_path=output_path,
        dry_run=False,
    )

    output_file = output_path / "activity.csv"
    meta_file = output_path / "meta.yaml"

    assert result.success is True
    assert output_file.exists(), "Pipeline should write output file"
    assert meta_file.exists(), "Pipeline should write metadata"

    df = pd.read_csv(output_file)
    assert len(df) == 2
    assert set(df["activity_id"].tolist()) == {1, 2}
