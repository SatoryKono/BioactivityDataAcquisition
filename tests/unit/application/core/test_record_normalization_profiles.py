"""Split normalization profile resolution and compatibility tests."""

from __future__ import annotations

from typing import cast
from unittest.mock import MagicMock

import pytest

from bioetl.application.core.pre_silver_record import PreSilverRecord
from bioetl.application.core.record_normalization_processor import (
    NormalizationContractError,
)

# ruff: noqa: F403
from tests.unit.application.core.normalization_test_support import *


pytestmark = pytest.mark.unit


def test_profile_auto_resolves_for_chembl_activity() -> None:
    processor = build_normalization_processor(
        provider="chembl",
        entity_type="activity",
    )

    normalized = processor.normalize_business_data(
        {
            "activity_id": " CHEMBL25 ",
            "publication_doi": " HTTPS://doi.org/10.1000/ABC ",
            "activity_properties": ' [{"rank":2,"kind":"b"},{"kind":"a","rank":1}] ',
        }
    )

    assert processor.profile is not None
    assert normalized["activity_id"] == "CHEMBL25"
    assert normalized["publication_doi"] == "10.1000/abc"
    assert (
        normalized["activity_properties"]
        == '[{"kind":"b","rank":2},{"kind":"a","rank":1}]'
    )


@pytest.mark.unit
def test_profile_backed_processor_rejects_unprofiled_business_field_by_default() -> (
    None
):
    processor = build_normalization_processor(
        provider="chembl",
        entity_type="activity",
    )

    with pytest.raises(NormalizationContractError, match="legacy_extra_field"):
        processor.normalize_business_data(
            {
                "activity_id": "CHEMBL25",
                "legacy_extra_field": "  needs explicit rule  ",
            }
        )


@pytest.mark.unit
def test_profile_backed_processor_can_enable_bounded_compatibility_fallback() -> None:
    processor = build_normalization_processor(
        provider="chembl",
        entity_type="activity",
        allow_compatibility_fallback=True,
    )

    normalized = processor.normalize_business_data(
        {
            "activity_id": "CHEMBL25",
            "legacy_extra_field": "  needs explicit rule  ",
        }
    )

    assert normalized["legacy_extra_field"] == "needs explicit rule"


@pytest.mark.unit
def test_profile_backed_processor_accepts_chembl_publication_oa_status() -> None:
    processor = build_normalization_processor(
        provider="chembl",
        entity_type="publication",
    )

    normalized = processor.normalize_business_data(
        {
            "publication_id": "CHEMBL25",
            "title": "Example",
            "publication_type": "journal-article",
            "oa_status": None,
        }
    )

    assert normalized["oa_status"] is None


@pytest.mark.unit
def test_processor_without_profile_keeps_legacy_fallback_behavior() -> None:
    processor = build_normalization_processor(
        provider="crossref",
        entity_type="ad_hoc_publication_payload",
    )

    normalized = processor.normalize_business_data(
        {
            "publication_doi": " HTTPS://doi.org/10.1000/ABC ",
            "legacy_extra_field": "  example value  ",
        }
    )

    assert processor.profile is None
    assert normalized["publication_doi"] == "10.1000/abc"
    assert normalized["legacy_extra_field"] == "example value"


@pytest.mark.unit
def test_profile_backed_processor_keeps_internal_meta_passthrough() -> None:
    processor = build_normalization_processor(
        provider="chembl",
        entity_type="activity",
    )

    normalized = processor.normalize_business_data(
        {
            "activity_id": "CHEMBL25",
            "_legacy_token": " keep-me ",
        }
    )

    assert normalized["_legacy_token"] == " keep-me "


@pytest.mark.unit
def test_profile_auto_resolves_for_chembl_molecule() -> None:
    processor = build_normalization_processor(
        provider="chembl",
        entity_type="molecule",
    )

    normalized = processor.normalize_business_data(
        {
            "molecule_id": " CHEMBL25 ",
            "pref_name": "  Example <b>Molecule</b>  ",
            "canonical_smiles": " CCO ",
            "molecular_weight": "123.4500000000",
        }
    )

    assert processor.profile is not None
    assert normalized["molecule_id"] == "CHEMBL25"
    assert normalized["pref_name"] == "Example Molecule"
    assert normalized["canonical_smiles"] == "CCO"
    assert normalized["molecular_weight"] == pytest.approx(123.45)


@pytest.mark.unit
def test_profile_auto_resolves_for_chembl_molecule_strict_json_fields() -> None:
    processor = build_normalization_processor(
        provider="chembl",
        entity_type="molecule",
    )

    normalized = processor.normalize_business_data(
        {
            "molecule_id": "CHEMBL25",
            "molecule_properties": ' {"b":2,"a":1} ',
            "cross_references": "{not json}",
        }
    )

    assert processor.profile is not None
    assert normalized["molecule_properties"] == '{"a":1,"b":2}'
    assert normalized["cross_references"] is None


@pytest.mark.unit
def test_profile_auto_resolves_for_semanticscholar_publication() -> None:
    processor = build_normalization_processor(
        provider="semanticscholar",
        entity_type="publication",
    )

    normalized = processor.normalize_business_data(
        {
            "paper_id": " S2:1 ",
            "title": "  Example <b>Title</b>  ",
            "doi": " HTTPS://doi.org/10.1000/ABC ",
            "pmid": " PMID:12345 ",
            "publication_date": "2024-02",
            "tldr": "  Short <i>summary</i>  ",
        }
    )

    assert processor.profile is not None
    assert normalized["paper_id"] == "S2:1"
    assert normalized["title"] == "Example Title"
    assert normalized["doi"] == "10.1000/abc"
    assert normalized["pmid"] == "12345"
    assert normalized["publication_date"] == "2024-02-29"
    assert normalized["tldr"] == "Short summary"


@pytest.mark.unit
def test_profile_auto_resolves_for_chembl_target_component() -> None:
    processor = build_normalization_processor(
        provider="chembl",
        entity_type="target_component",
    )

    normalized = processor.normalize_business_data(
        {
            "component_id": " 42 ",
            "taxonomy_id": " 9606 ",
            "protein_classification_id": " 7 ",
            "target_component_synonyms": ' [{"name":"B"},{"name":"A"}] ',
            "protein_classification_ids": " [7, 3, 5] ",
            "organism": "  homo   sapiens ",
        }
    )

    assert processor.profile is not None
    assert normalized["component_id"] == 42
    assert normalized["taxonomy_id"] == 9606
    assert normalized["protein_classification_id"] == 7
    assert normalized["target_component_synonyms"] == '[{"name":"B"},{"name":"A"}]'
    assert normalized["protein_classification_ids"] == "[7,3,5]"
    assert normalized["organism"] == "Homo sapiens"


@pytest.mark.unit
def test_profile_auto_resolves_for_chembl_cell_line() -> None:
    processor = build_normalization_processor(
        provider="chembl",
        entity_type="cell_line",
    )

    normalized = processor.normalize_business_data(
        {
            "cell_id": "CHEMBL1",
            "cell_name": "  HeLa ",
            "cellosaurus_id": " cvcl:0030 ",
        }
    )

    assert processor.profile is not None
    assert normalized["cell_name"] == "HeLa"
    assert normalized["cellosaurus_id"] == "CVCL_0030"


@pytest.mark.unit
def test_profile_auto_resolves_for_chembl_publication_runtime_mismatches_and_strict_json() -> (
    None
):
    processor = build_normalization_processor(
        provider="chembl",
        entity_type="publication",
    )

    normalized = processor.normalize_business_data(
        {
            "publication_id": "CHEMBL123",
            "title": " Example publication ",
            "publication_type": " PUBLICATION ",
            "is_oa": "1",
            "authors": ' {"b":2,"a":1} ',
            "affiliation_list": "not-json",
        }
    )

    assert processor.profile is not None
    assert normalized["publication_type"] == "journal-article"
    assert normalized["is_oa"] is True
    assert normalized["authors"] == '{"a":1,"b":2}'
    assert normalized["affiliation_list"] is None


@pytest.mark.unit
def test_finalize_pre_silver_projects_malformed_json_findings_to_dq_warning() -> None:
    processor = build_normalization_processor(
        provider="chembl",
        entity_type="publication",
    )
    mock_logger = MagicMock()
    mock_logger.warning = MagicMock()
    mock_context = MagicMock()
    mock_context.logger = mock_logger
    pre_silver = PreSilverRecord(
        entity_id="chembl:publication:1",
        business_data={
            "publication_id": "CHEMBL123",
            "title": "Example publication",
            "publication_type": "PUBLICATION",
            "affiliation_list": "not-json",
        },
        build_silver_record=lambda _context, entity_id, content_hash, _index, business: {
            "entity_id": entity_id,
            "content_hash": content_hash,
            **business,
        },
    )

    silver_record = processor.finalize_pre_silver(
        pre_silver,
        context=cast("PipelineContext", mock_context),
        index=7,
    )

    assert silver_record is not None
    assert silver_record["affiliation_list"] is None
    assert silver_record["_dq_warn"] is True
    assert len(processor.normalization_findings) == 1
    finding = processor.normalization_findings[0]
    assert finding.field_name == "affiliation_list"
    assert finding.reason_code == "malformed_json_normalized_to_null"
    mock_logger.warning.assert_called_once_with(
        "silver_normalization_malformed_json",
        provider="chembl",
        entity_type="publication",
        record_index=7,
        reason_code="malformed_json_normalized_to_null",
        field="affiliation_list",
        action_taken="set_null_and_warn",
        dq_warn=True,
        proposed_normalized_outcome=None,
    )
