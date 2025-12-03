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
    reset_provider_registry,
    restore_provider_registry,
)
from bioetl.domain.providers import ProviderId  # noqa: E402
from bioetl.infrastructure.clients.chembl.provider import (  # noqa: E402
    register_chembl_provider,
)
from bioetl.infrastructure.config.models import PipelineConfig  # noqa: E402
from bioetl.schemas.provider_config_schema import ChemblSourceConfig


@pytest.fixture(autouse=True)
def _restore_registry() -> None:
    snapshot = list_providers()
    yield
    restore_provider_registry(snapshot)


def test_get_extraction_service_for_chembl() -> None:
    register_chembl_provider()
    container = PipelineContainer(
        PipelineConfig(
            id="chembl.activity",
            provider="chembl",
            entity="activity",
            input_mode="auto_detect",
            input_path=None,
            output_path="/tmp/out",
            batch_size=10,
            provider_config=ChemblSourceConfig(
                base_url="https://www.ebi.ac.uk/chembl/api/data",
                timeout_sec=30,
                max_retries=3,
                rate_limit_per_sec=10.0,
            ),
        )
    )

    service = container.get_extraction_service()

    from bioetl.application.services.chembl_extraction import (
        ChemblExtractionService,
    )

    assert isinstance(service, ChemblExtractionService)


def test_unknown_provider_raises() -> None:
    reset_provider_registry()
    container = PipelineContainer(
        PipelineConfig(
            id="chembl.activity",
            provider="chembl",
            entity="activity",
            input_mode="auto_detect",
            input_path=None,
            output_path="/tmp/out",
            batch_size=10,
            provider_config=ChemblSourceConfig(
                base_url="https://www.ebi.ac.uk/chembl/api/data",
                timeout_sec=30,
                max_retries=3,
                rate_limit_per_sec=10.0,
            ),
        )
    )

    with pytest.raises(ProviderNotRegisteredError):
        container.get_extraction_service()


def test_config_validation_error_is_propagated() -> None:
    with pytest.raises(ValidationError):
        PipelineConfig(
            id="chembl.activity",
            provider="chembl",
            entity="activity",
            input_mode="auto_detect",
            input_path=None,
            output_path="/tmp/out",
            batch_size=10,
            provider_config=ChemblSourceConfig(
                base_url="https://www.ebi.ac.uk/chembl/api/data",
                timeout_sec=30,
                max_retries=3,
                rate_limit_per_sec=10.0,
                max_url_length=0,
            ),
        )
