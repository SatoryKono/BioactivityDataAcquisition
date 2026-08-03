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
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Contract tests for shared Gold publication schema constraints."""

from __future__ import annotations

import pandas as pd
import pandera as pa
import pytest

import bioetl.domain.contracts.gold._publication_common_schema as publication_common_schema
from bioetl.domain.contracts.gold._publication_common_schema import (
    PublicationGoldCommonSchema,
)
from bioetl.domain.schemas.common.publication_base import LOOKUP_METHODS
from tests.contract.schemas._schema_row_helpers import minimal_schema_dataframe
from tests.helpers.publication_type_classification import (
    initialize_test_publication_type_classification,
)

pytestmark = [pytest.mark.contracts, pytest.mark.no_api]


def _minimal_publication_common_df() -> pd.DataFrame:
    frame = minimal_schema_dataframe(PublicationGoldCommonSchema)
    frame.loc[0, "entity_id"] = "publication:test"
    frame.loc[0, "content_hash"] = "a" * 64
    frame.loc[0, "doi"] = "10.1000/xyz"
    frame.loc[0, "pmid"] = "12345678"
    frame.loc[0, "title"] = "Test title"
    frame.loc[0, "_source"] = "pubmed"
    frame.loc[0, "_lookup_method"] = LOOKUP_METHODS[0]
    return frame


def test_publication_common_schema_accepts_minimal_row() -> None:
    validated = PublicationGoldCommonSchema.validate(_minimal_publication_common_df())
    assert validated["entity_id"].iloc[0] == "publication:test"


def test_publication_common_schema_accepts_loaded_taxonomy_values() -> None:
    initialize_test_publication_type_classification()
    frame = _minimal_publication_common_df()
    frame.loc[0, "publication_type_unified"] = "Journal Article"
    frame.loc[0, "publication_subclass"] = "Original Experimental Data"
    frame.loc[0, "publication_class"] = "EXP"
    validated = PublicationGoldCommonSchema.validate(frame)
    assert validated["publication_class"].iloc[0] == "EXP"


def test_publication_common_schema_rejects_invalid_lookup_method() -> None:
    df = _minimal_publication_common_df()
    df.loc[0, "_lookup_method"] = "invalid-method"
    with pytest.raises(pa.errors.SchemaError):
        PublicationGoldCommonSchema.validate(df)


def test_publication_common_schema_rejects_invalid_doi() -> None:
    df = _minimal_publication_common_df()
    df.loc[0, "doi"] = "not-a-doi"
    with pytest.raises(pa.errors.SchemaError):
        PublicationGoldCommonSchema.validate(df)


def test_publication_common_schema_rejects_invalid_loaded_taxonomy_value() -> None:
    initialize_test_publication_type_classification()
    frame = _minimal_publication_common_df()
    frame.loc[0, "publication_class"] = "BAD"
    with pytest.raises(pa.errors.SchemaError):
        PublicationGoldCommonSchema.validate(frame)


def test_publication_common_schema_allows_values_when_taxonomy_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        publication_common_schema,
        "publication_classification_values",
        lambda _field_name: [],
    )
    frame = _minimal_publication_common_df()
    frame.loc[0, "publication_type_unified"] = "Provider Specific Type"
    validated = PublicationGoldCommonSchema.validate(frame)
    assert validated["publication_type_unified"].iloc[0] == "Provider Specific Type"
