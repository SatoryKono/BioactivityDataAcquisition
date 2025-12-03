from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

sys.modules.setdefault("tqdm", SimpleNamespace(tqdm=lambda *args: None))

from bioetl.application.container import PipelineContainer  # noqa: E402
from bioetl.domain.provider_registry import (  # noqa: E402
    ProviderNotRegisteredError,
    list_providers,
    restore_provider_registry,
)
from bioetl.domain.providers import ProviderId  # noqa: E402
from bioetl.infrastructure.clients.chembl.provider import (  # noqa: E402
    register_chembl_provider,
)
from bioetl.infrastructure.config.models import PipelineConfig  # noqa: E402


@pytest.fixture(autouse=True)
def _restore_registry() -> None:
    snapshot = list_providers()
    yield
    restore_provider_registry(snapshot)


def test_get_extraction_service_for_chembl() -> None:
    register_chembl_provider()
    container = PipelineContainer(
        PipelineConfig(
            provider=ProviderId.CHEMBL,
            entity_name="activity",
            sources={},
        )
    )

    service = container.get_extraction_service()

    from bioetl.application.services.chembl_extraction import (
        ChemblExtractionService,
    )

    assert isinstance(service, ChemblExtractionService)


def test_unknown_provider_raises() -> None:
    container = PipelineContainer(
        PipelineConfig(
            provider=ProviderId.PUBCHEM,
            entity_name="compound",
            sources={},
        )
    )

    with pytest.raises(ProviderNotRegisteredError):
        container.get_extraction_service()


def test_config_validation_error_is_propagated() -> None:
    register_chembl_provider()
    container = PipelineContainer(
        PipelineConfig(
            provider=ProviderId.CHEMBL,
            entity_name="activity",
            sources={"chembl": {"max_url_length": 0}},
        )
    )

    with pytest.raises(ValidationError):
        container.get_extraction_service()
