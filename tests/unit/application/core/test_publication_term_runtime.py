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
"""Unit contracts for derived ChEMBL publication-term runtime extraction."""

from __future__ import annotations

import pytest

from bioetl.application.core.publication_term_runtime import (
    create_term_record,
    extract_terms_from_publication,
    mesh_terms_from_pubmed_headings,
    publication_pubmed_id,
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


def test_extract_mesh_rejects_non_string_and_blank_fields() -> None:
    publication = {
        "mesh_terms": [
            {
                "mesh_heading": "  ",
                "mesh_id": "D1",
                "mesh_qualifier": "use",
            },
            {
                "mesh_heading": 123,
                "mesh_id": "D2",
                "mesh_qualifier": "x",
            },
            {
                "mesh_heading": "valid heading",
                "mesh_id": 999,
                "mesh_qualifier": "  ",
            },
            {
                "mesh_heading": "kinase",
                "mesh_id": " D004791 ",
                "mesh_qualifier": " therapeutic use ",
            },
        ],
        "keywords": ["ok", "  ", 5, None],
    }

    terms = extract_terms_from_publication(publication, "CHEMBL9")

    # blank heading skipped; non-str heading skipped; blank qualifier omitted;
    # valid heading kept with non-str mesh_id -> None; last mesh has full fields
    types = [t["term_type"] for t in terms]
    assert "KEYWORD" in types
    assert types.count("KEYWORD") == 1
    assert terms[-1]["term"] == "ok" or any(t["term"] == "ok" for t in terms)

    heading = next(t for t in terms if t["term"] == "kinase")
    assert heading["term_type"] == "MESH_HEADING"
    assert heading["mesh_id"] == "D004791"
    assert heading["qualifier"] == "therapeutic use"

    qualifier = next(t for t in terms if t["term"] == "therapeutic use")
    assert qualifier["term_type"] == "MESH_QUALIFIER"
    assert qualifier["mesh_id"] == "D004791"


def test_create_term_record_normalizes_mesh_id_and_qualifier() -> None:
    record = create_term_record(
        publication_id="CHEMBL1",
        term="enzyme",
        term_type="MESH_HEADING",
        mesh_id="  D1  ",
        qualifier="  use  ",
    )
    assert record["mesh_id"] == "D1"
    assert record["qualifier"] == "use"


def test_publication_pubmed_id_accepts_positive_int_and_string() -> None:
    assert publication_pubmed_id({"pubmed_id": 17827018}) == "17827018"
    assert publication_pubmed_id({"pubmed_id": " 17827018 "}) == "17827018"
    assert publication_pubmed_id({"pubmed_id": 0}) is None
    assert publication_pubmed_id({"pubmed_id": ""}) is None
    assert publication_pubmed_id({}) is None


def test_mesh_terms_from_pubmed_headings_maps_descriptor_and_extra_qualifiers() -> None:
    mesh_terms, keywords = mesh_terms_from_pubmed_headings(
        [
            {
                "descriptor_name": "Acetylene",
                "descriptor_ui": "D000114",
                "qualifiers": [
                    {"name": "pharmacology"},
                    {"name": "chemistry"},
                ],
            },
            {
                "descriptor_name": "Humans",
                "descriptor_ui": "D006801",
                "qualifiers": [],
            },
            {"descriptor_ui": "D000000"},
        ],
        keywords=[" bioactivity ", "", 1],
    )

    assert mesh_terms == [
        {
            "mesh_heading": "Acetylene",
            "mesh_id": "D000114",
            "mesh_qualifier": "pharmacology",
        },
        {
            "mesh_heading": None,
            "mesh_id": "D000114",
            "mesh_qualifier": "chemistry",
        },
        {
            "mesh_heading": "Humans",
            "mesh_id": "D006801",
            "mesh_qualifier": None,
        },
    ]
    assert keywords == ["bioactivity"]

    terms = extract_terms_from_publication(
        {"mesh_terms": mesh_terms, "keywords": keywords},
        "CHEMBL1137491",
    )
    types_and_terms = [(term["term_type"], term["term"]) for term in terms]
    assert types_and_terms == [
        ("MESH_HEADING", "Acetylene"),
        ("MESH_QUALIFIER", "pharmacology"),
        ("MESH_QUALIFIER", "chemistry"),
        ("MESH_HEADING", "Humans"),
        ("KEYWORD", "bioactivity"),
    ]
