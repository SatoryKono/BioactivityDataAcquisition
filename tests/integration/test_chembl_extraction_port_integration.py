"""Integration test for the ChEMBL extraction port implementation."""

from functools import partial
from pathlib import Path

import pytest

from bioetl.application.config.runtime import build_runtime_config
from bioetl.domain.clients.ports import ChemblExtractionPortABC
from bioetl.infrastructure.clients.chembl import ChemblExtractionClientImpl
from bioetl.infrastructure.clients.provider_registry_loader import (
    create_provider_loader,
)
from bioetl.interfaces.wiring import build_default_container, create_config_loader


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

    config_loader = create_config_loader()
    config = build_runtime_config(
        config_path=Path("tests/fixtures/configs/chembl_activity_test.yaml"),
        configs_root=Path("tests/fixtures/configs"),
        loader=config_loader,
    )

    provider_loader_factory = partial(create_provider_loader)
    registry = provider_loader_factory().get_registry()
    container = build_default_container(config, provider_registry=registry)

    service = container.get_extraction_service()

    assert isinstance(service, ChemblExtractionPortABC)
    assert isinstance(service, ChemblExtractionClientImpl)
    assert service.get_release_version() == "chembl_port_integration"
