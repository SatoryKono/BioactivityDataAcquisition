# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Compatibility tests for PubChem fetch strategy facade imports."""

from __future__ import annotations


import pytest

pytestmark = pytest.mark.unit


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
    assert "normalize_pubchem_results" in response_mapper.__all__
    assert "build_compound_name_endpoint" in query_builder.__all__
    assert "is_limit_reached" in policy_helper.__all__
