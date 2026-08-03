# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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
"""Tests for shared Gold publication contract governance."""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pa
import pytest

from bioetl.domain.contracts.gold import _publication_common_schema
from bioetl.domain.contracts.gold._publication_common_schema import (
    PublicationGoldCommonSchema,
)


pytestmark = pytest.mark.unit


def _publication_gold_frame(**overrides: object) -> pd.DataFrame:
    record: dict[str, object] = {
        "entity_id": "publication:1",
        "content_hash": "hash",
        "doi": "10.1000/example",
        "pmid": None,
        "pmc_id": None,
        "title": "Title",
        "abstract": None,
        "authors": None,
        "affiliation_list": None,
        "journal": None,
        "issn": None,
        "issn_list": None,
        "volume": None,
        "issue": None,
        "page_first": None,
        "page_last": None,
        "publication_year": 2025,
        "publication_date": "2025-01-01",
        "publication_type": "article",
        "publication_type_unified": "Journal Article",
        "publication_subclass": "Original Experimental Data",
        "publication_class": "EXP",
        "citations_made": 0,
        "_source": "openalex",
        "_lookup_method": "doi",
        "_original_id": "W1",
        "_dq_warn": False,
        "_dq_error": False,
        "_index": 0,
    }
    record.update(overrides)
    return pd.DataFrame([record])


def test_publication_gold_contract_accepts_loaded_taxonomy_values(
    publication_type_classification_data: None,
) -> None:
    validated = PublicationGoldCommonSchema.validate(_publication_gold_frame())

    assert validated["publication_type_unified"].iloc[0] == "Journal Article"


def test_publication_gold_contract_rejects_unknown_derived_taxonomy_values(
    publication_type_classification_data: None,
) -> None:
    with pytest.raises(pa.errors.SchemaError):
        PublicationGoldCommonSchema.validate(
            _publication_gold_frame(publication_type_unified="not-a-taxonomy-value")
        )


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("publication_subclass", "not-a-taxonomy-value"),
        ("publication_class", "not-a-taxonomy-value"),
    ],
)
def test_publication_gold_contract_rejects_unknown_secondary_taxonomy_values(
    publication_type_classification_data: None,
    field_name: str,
    invalid_value: str,
) -> None:
    with pytest.raises(pa.errors.SchemaError):
        PublicationGoldCommonSchema.validate(
            _publication_gold_frame(**{field_name: invalid_value})
        )


@pytest.mark.parametrize(
    "overrides",
    [
        {"doi": "not-a-doi"},
        {"publication_year": 1499},
        {"citations_made": -1},
        {"_lookup_method": "not-supported"},
    ],
)
def test_publication_gold_contract_rejects_invalid_field_constraints(
    publication_type_classification_data: None,
    overrides: dict[str, object],
) -> None:
    with pytest.raises(pa.errors.SchemaError):
        PublicationGoldCommonSchema.validate(_publication_gold_frame(**overrides))


def test_publication_gold_contract_allows_any_taxonomy_value_when_not_loaded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        _publication_common_schema,
        "publication_classification_values",
        lambda field_name: frozenset(),
    )

    validated = PublicationGoldCommonSchema.validate(
        _publication_gold_frame(
            publication_type_unified="custom-type",
            publication_subclass="custom-subclass",
            publication_class="custom-class",
        )
    )

    assert validated["publication_type_unified"].iloc[0] == "custom-type"
    assert validated["publication_subclass"].iloc[0] == "custom-subclass"
    assert validated["publication_class"].iloc[0] == "custom-class"
