"""Explicit provider registration for Composition layer.

Loads config from configs/providers/*.yaml. HttpConfig serves as fallback.
Config helpers extracted to _config_helpers.py per audit-package-structure-2026-02-07.
Creator functions extracted to registration_bio.py and registration_biblio.py.
"""

from __future__ import annotations

from bioetl.application.core.idmapping_data_source import IDMappingDataSource
from bioetl.composition.providers._config_helpers import _get_rate_limit_from_config
from bioetl.composition.providers.provider_registry import (
    HttpConfig,
    ProviderConfig,
    ProviderRegistry,
)
from bioetl.composition.providers.registration_biblio import (
    _create_crossref_data_source,
    _create_openalex_data_source,
    _create_pubmed_data_source,
    _create_semanticscholar_data_source,
)
from bioetl.composition.providers.registration_bio import (
    _create_chembl_data_source,
    _create_pubchem_adapter,
    _create_pubchem_data_source,
    _create_uniprot_data_source,
    _create_uniprot_idmapping_data_source,
)

# Import adapter classes for ProviderConfig (allowed direction)
from bioetl.infrastructure.adapters.chembl.client import ChemblAdapter
from bioetl.infrastructure.adapters.crossref.client import (
    CrossRefAdapter,
)
from bioetl.infrastructure.adapters.crossref.factory import (
    _create_crossref_adapter,
)
from bioetl.infrastructure.adapters.openalex.client import (
    OpenAlexAdapter,
    _create_openalex_adapter,
)
from bioetl.infrastructure.adapters.pubchem.client import PubChemAdapter
from bioetl.infrastructure.adapters.pubmed.pubmed_client import (
    PubMedAdapter,
    _create_pubmed_adapter,
)
from bioetl.infrastructure.adapters.semanticscholar.adapter import (
    SemanticScholarAdapter,
)
from bioetl.infrastructure.adapters.uniprot.client import UniProtAdapter

__all__ = [
    "register_all_providers",
]


# =============================================================================
# Provider registration
# =============================================================================


def register_all_providers() -> None:
    """Explicitly register all data source providers.

    This function MUST be called from bootstrap before using ProviderRegistry.
    Idempotent - safe to call multiple times.

    Configuration Priority:
    1. configs/providers/{provider}.yaml - PRIMARY (rate limits, circuit breaker, batch_size)
    2. HttpConfig in ProviderConfig - FALLBACK only

    Each provider includes a data_source_creator for unified registry access.
    """
    for provider_name, config in _build_provider_configs().items():
        if ProviderRegistry.is_registered(provider_name):
            continue
        ProviderRegistry.register(provider_name, config)


def _build_provider_configs() -> dict[str, ProviderConfig]:
    """Build provider registry configs from YAML-backed rate limits."""
    chembl = _get_rate_limit_from_config("chembl")
    pubchem = _get_rate_limit_from_config("pubchem")
    uniprot = _get_rate_limit_from_config("uniprot")
    pubmed = _get_rate_limit_from_config("pubmed")
    crossref = _get_rate_limit_from_config("crossref")
    openalex = _get_rate_limit_from_config("openalex")
    semanticscholar = _get_rate_limit_from_config("semanticscholar")

    return {
        "chembl": ProviderConfig(
            adapter_class=ChemblAdapter,
            http_config=HttpConfig(rate=chembl.rate, capacity=chembl.capacity),
            requires_http_client=True,
            requires_logger=True,
            data_source_creator=_create_chembl_data_source,
        ),
        "pubchem": ProviderConfig(
            adapter_class=PubChemAdapter,
            http_config=HttpConfig(rate=pubchem.rate, capacity=pubchem.capacity),
            requires_http_client=False,
            requires_logger=True,
            custom_creator=_create_pubchem_adapter,
            data_source_creator=_create_pubchem_data_source,
        ),
        "uniprot": ProviderConfig(
            adapter_class=UniProtAdapter,
            http_config=HttpConfig(
                rate=uniprot.rate,
                capacity=uniprot.capacity,
                rate_overrides={"uniprot_api_key": 100.0},
            ),
            requires_http_client=True,
            requires_logger=True,
            data_source_creator=_create_uniprot_data_source,
        ),
        "pubmed": ProviderConfig(
            adapter_class=PubMedAdapter,
            http_config=HttpConfig(
                rate=pubmed.rate,
                capacity=pubmed.capacity,
                rate_overrides={"pubmed_api_key": 10.0},
            ),
            requires_http_client=True,
            requires_logger=True,
            custom_creator=_create_pubmed_adapter,
            data_source_creator=_create_pubmed_data_source,
        ),
        "crossref": ProviderConfig(
            adapter_class=CrossRefAdapter,
            http_config=HttpConfig(rate=crossref.rate, capacity=crossref.capacity),
            requires_http_client=True,
            requires_logger=True,
            custom_creator=_create_crossref_adapter,
            data_source_creator=_create_crossref_data_source,
        ),
        "openalex": ProviderConfig(
            adapter_class=OpenAlexAdapter,
            http_config=HttpConfig(rate=openalex.rate, capacity=openalex.capacity),
            requires_http_client=True,
            requires_logger=True,
            custom_creator=_create_openalex_adapter,
            data_source_creator=_create_openalex_data_source,
        ),
        "semanticscholar": ProviderConfig(
            adapter_class=SemanticScholarAdapter,
            http_config=HttpConfig(
                rate=semanticscholar.rate,
                capacity=semanticscholar.capacity,
            ),
            requires_http_client=True,
            requires_logger=True,
            data_source_creator=_create_semanticscholar_data_source,
        ),
        "uniprot_idmapping": ProviderConfig(
            adapter_class=IDMappingDataSource,
            http_config=HttpConfig(rate=uniprot.rate, capacity=uniprot.capacity),
            requires_http_client=True,
            requires_logger=True,
            data_source_creator=_create_uniprot_idmapping_data_source,
        ),
    }
