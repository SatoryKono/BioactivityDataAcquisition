"""Unit contracts for derived ChEMBL publication-term runtime extraction."""

from __future__ import annotations

import pytest

from bioetl.application.core.publication_term_runtime import (
    create_term_record,
    extract_terms_from_publication,
)
from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)


pytestmark = pytest.mark.unit


def test_create_term_record_trims_source_term_before_profile_normalization() -> None:
    record = create_term_record(
        publication_id="CHEMBL1",
        term="  kinase inhibitor  ",
        term_type="KEYWORD",
        mesh_id=None,
        qualifier=None,
    )

    assert record["term"] == "kinase inhibitor"
    assert record["term_type"] == "KEYWORD"
    assert len(str(record["entity_id"])) == 16

    normalized = RecordNormalizationProcessor(
        provider="chembl",
        entity_type="publication_term",
    ).normalize_business_data(record)

    assert normalized["term"] == "kinase inhibitor"
    assert normalized["term_type"] == "KEYWORD"


def test_extract_terms_from_publication_preserves_mesh_shape_and_keyword_semantics() -> (
    None
):
    publication = {
        "mesh_terms": [
            {
                "mesh_heading": "enzyme inhibitors",
                "mesh_id": "mesh:d004791",
                "mesh_qualifier": "therapeutic use",
            }
        ],
        "keywords": [" kinase ", " inhibitor "],
    }

    terms = extract_terms_from_publication(publication, "CHEMBL1")

    assert [term["term_type"] for term in terms] == [
        "MESH_HEADING",
        "MESH_QUALIFIER",
        "KEYWORD",
        "KEYWORD",
    ]
    assert terms[0]["mesh_id"] == "mesh:d004791"
    assert terms[0]["qualifier"] == "therapeutic use"
    assert terms[1]["qualifier"] is None
    assert terms[2]["term"] == "kinase"
    assert terms[3]["term"] == "inhibitor"
