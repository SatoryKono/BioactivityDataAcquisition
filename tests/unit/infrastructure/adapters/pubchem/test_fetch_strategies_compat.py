"""Compatibility tests for PubChem fetch strategy facade imports."""

from __future__ import annotations


def test_fetch_strategies_import_path_is_stable() -> None:
    """Legacy import path should keep exporting PubChemFetchStrategies."""
    from bioetl.infrastructure.adapters.pubchem.fetch_strategies import (
        PubChemFetchStrategies,
    )

    assert PubChemFetchStrategies.__name__ == "PubChemFetchStrategies"


def test_fetch_strategies_module_all_contains_public_facade() -> None:
    """Facade module __all__ should expose only compatibility surface."""
    from bioetl.infrastructure.adapters.pubchem import fetch_strategies

    assert fetch_strategies.__all__ == ["PubChemFetchStrategies"]


def test_pubchem_helper_modules_expose_contract_symbols() -> None:
    """Extracted helper modules should expose stable contract names."""
    from bioetl.infrastructure.adapters.pubchem import (
        fetch_flow,
        policy_helper,
        query_builder,
        response_mapper,
    )

    assert "PubChemFetchFlow" in fetch_flow.__all__
    assert "PubChemFetchFlowService" in fetch_flow.__all__
    assert "normalize_pubchem_results" in response_mapper.__all__
    assert "build_compound_name_endpoint" in query_builder.__all__
    assert "is_limit_reached" in policy_helper.__all__
