"""Integration test for the ChEMBL extraction port implementation."""

from functools import partial
from pathlib import Path

import pytest

from bioetl.application.config.runtime import build_runtime_config
from bioetl.application.container import build_pipeline_dependencies
from bioetl.domain.clients.ports.chembl_extraction_port import ChemblExtractionPort
from bioetl.infrastructure.clients.chembl import ChemblExtractionClientImpl
from bioetl.infrastructure.clients.provider_registry_loader import (
    create_provider_loader,
)


@pytest.mark.integration
def test_chembl_extraction_port_is_resolved(monkeypatch: pytest.MonkeyPatch) -> None:
    """Container wiring returns the ChEMBL extraction port implementation."""

    monkeypatch.setenv(
        "BIOETL_CONFIG_DIR", str(Path("tests/fixtures/configs").resolve())
    )
    monkeypatch.setattr(
        ChemblExtractionClientImpl,
        "get_release_version",
        lambda self: "chembl_port_integration",
    )

    config = build_runtime_config(
        config_path=Path("tests/fixtures/configs/chembl_activity_test.yaml"),
        configs_root=Path("tests/fixtures/configs"),
    )

    provider_loader_factory = partial(create_provider_loader)
    registry = provider_loader_factory().load_registry()
    container = build_pipeline_dependencies(config, provider_registry=registry)

    service = container.get_extraction_service()

    assert isinstance(service, ChemblExtractionPort)
    assert isinstance(service, ChemblExtractionClientImpl)
    assert service.get_release_version() == "chembl_port_integration"
