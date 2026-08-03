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
"""Tests for ChEMBL provider-native alias normalization."""

from __future__ import annotations

import pytest

from bioetl.application.pipelines.chembl.alias_policy import (
    CHEMBL_ALIAS_POLICY_VERSION,
    CHEMBL_BRONZE_PROVIDER_ALIASES,
    CHEMBL_GOLD_PUBLICATION_IDENTIFIER_PROJECTIONS,
    get_bronze_provider_aliases,
)
from bioetl.application.pipelines.chembl.provider_aliases import (
    normalize_provider_aliases,
)


pytestmark = pytest.mark.unit


def test_normalize_provider_aliases_copies_provider_native_values() -> None:
    """Provider-native payload fields should populate canonical internal fields."""
    record = {"assay_chembl_id": "CHEMBL123"}

    normalized = normalize_provider_aliases(record, {"assay_id": "assay_chembl_id"})

    assert normalized["assay_id"] == "CHEMBL123"
    assert normalized["assay_chembl_id"] == "CHEMBL123"
    assert "assay_id" not in record


def test_normalize_provider_aliases_preserves_existing_canonical_values() -> None:
    """Already canonical staged payloads should not be overwritten."""
    record = {"assay_id": "CANONICAL", "assay_chembl_id": "PROVIDER"}

    normalized = normalize_provider_aliases(record, {"assay_id": "assay_chembl_id"})

    assert normalized is record
    assert normalized["assay_id"] == "CANONICAL"


def test_chembl_alias_policy_versions_bronze_provider_aliases() -> None:
    """Provider-native aliases must be discoverable by policy version and entity."""
    assert CHEMBL_ALIAS_POLICY_VERSION == "chembl-alias-policy.v1"
    assert get_bronze_provider_aliases("activity") == {
        "molecule_id": "molecule_chembl_id"
    }
    assert get_bronze_provider_aliases("tissue") == {"tissue_id": "tissue_chembl_id"}
    assert get_bronze_provider_aliases("unknown") == {}
    assert set(CHEMBL_BRONZE_PROVIDER_ALIASES) == {"activity", "tissue"}


def test_chembl_publication_identifier_projections_are_separate_from_bronze_aliases() -> (
    None
):
    """Gold publication projections must not be mixed into Bronze provider aliases."""
    assert "publication_doi" not in CHEMBL_BRONZE_PROVIDER_ALIASES.get(
        "activity",
        {},
    )
    assert CHEMBL_GOLD_PUBLICATION_IDENTIFIER_PROJECTIONS["publication_doi"] == (
        "publication_doi",
        "doi",
        "document_doi",
    )
