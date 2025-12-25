"""Explicit provider registration.

Centralizes all provider registrations in the Composition layer.
This ensures Infrastructure layer does NOT import from Composition.

This module follows the Hexagonal Architecture import matrix:
- Composition CAN import from Infrastructure (allowed)
- Infrastructure MUST NOT import from Composition (forbidden)
"""

from __future__ import annotations

from bioetl.composition.providers.provider_registry import (
    HttpConfig,
    ProviderConfig,
    ProviderRegistry,
)

# Import adapter classes from Infrastructure (allowed direction)
from bioetl.infrastructure.adapters.chembl.client import ChemblAdapter
from bioetl.infrastructure.adapters.pubchem.client import PubChemAdapter
from bioetl.infrastructure.adapters.pubmed.pubmed_client import (
    PubMedAdapter,
    _create_pubmed_adapter,
)
from bioetl.infrastructure.adapters.uniprot.client import UniProtAdapter


def register_all_providers() -> None:
    """Explicitly register all data source providers.

    This function MUST be called from bootstrap before using ProviderRegistry.
    Idempotent - safe to call multiple times.

    Provider configurations:
    - ChEMBL: 10 req/sec, capacity 20 (async HTTP client)
    - PubChem: 5 req/sec, capacity 10 (sync via ThreadPoolExecutor)
    - UniProt: 10 req/sec, 100 with API key, capacity 20 (async HTTP client)
    - PubMed: 3 req/sec, 10 with API key, capacity 6 (async HTTP client)
    """
    # ChEMBL - async HTTP adapter
    if not ProviderRegistry.is_registered("chembl"):
        ProviderRegistry.register(
            "chembl",
            ProviderConfig(
                adapter_class=ChemblAdapter,
                http_config=HttpConfig(
                    rate=10.0,
                    capacity=20,
                ),
                requires_http_client=True,
                requires_logger=True,
            ),
        )

    # PubChem - sync adapter (uses internal ThreadPoolExecutor)
    if not ProviderRegistry.is_registered("pubchem"):
        ProviderRegistry.register(
            "pubchem",
            ProviderConfig(
                adapter_class=PubChemAdapter,
                http_config=HttpConfig(
                    rate=5.0,
                    capacity=10,
                ),
                requires_http_client=False,
                requires_logger=True,
            ),
        )

    # UniProt - async HTTP adapter with conditional rate override
    if not ProviderRegistry.is_registered("uniprot"):
        ProviderRegistry.register(
            "uniprot",
            ProviderConfig(
                adapter_class=UniProtAdapter,
                http_config=HttpConfig(
                    rate=10.0,
                    capacity=20,
                    rate_overrides={"uniprot_api_key": 100.0},
                ),
                requires_http_client=True,
                requires_logger=True,
            ),
        )

    # PubMed - async HTTP adapter with custom creator for email/API key handling
    if not ProviderRegistry.is_registered("pubmed"):
        ProviderRegistry.register(
            "pubmed",
            ProviderConfig(
                adapter_class=PubMedAdapter,
                http_config=HttpConfig(
                    rate=3.0,
                    capacity=6,
                    rate_overrides={"pubmed_api_key": 10.0},
                ),
                requires_http_client=True,
                requires_logger=True,
                custom_creator=_create_pubmed_adapter,
            ),
        )
