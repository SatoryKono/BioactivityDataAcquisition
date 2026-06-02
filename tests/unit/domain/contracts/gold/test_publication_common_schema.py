"""Tests for shared Gold publication contract governance."""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pa
import pytest

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
