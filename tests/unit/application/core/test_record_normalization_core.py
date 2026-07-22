"""Split core normalization behavior tests."""

from __future__ import annotations

import pytest

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.application.core.pre_silver_adapter_mixin import PreSilverAdapterMixin
from bioetl.application.core.record_normalization_finalization import (
    finalize_pre_silver_record,
)
from bioetl.domain.context import PipelineContext
from bioetl.domain.filtering.column_filter import GoldColumnFilter
from bioetl.domain.filtering.silver_config import SilverFilterConfig
from bioetl.domain.transformations.hashing import generate_content_hash
from bioetl.domain.types import RunType
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite
from tests.helpers.transformer_dependencies import build_test_transformer_dependencies

# ruff: noqa: F403
from tests.unit.application.core.normalization_test_support import *


pytestmark = pytest.mark.unit


class _PreSilverFilterTransformer(PreSilverAdapterMixin, BaseTransformer):
    async def _transform_impl(self, context, record, index):
        del context, record, index
        return None


class _PreSilverFinalizerHarness:
    content_hash_policy_by_version = None

    def normalize_business_data(self, business_data):
        return {"normalized": business_data["raw"].strip()}

    def compute_content_hashes_by_version(self, record):
        del record
        return {}

    def compute_content_hash(self, record):
        return f"hash:{record['normalized']}"

    def project_normalization_findings(self, record, *, context=None, index=None):
        del context
        return {**record, "projected_index": index}

    def _should_project_hashes_by_version(self):
        return False


def _pipeline_context() -> PipelineContext:
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    logger.debug = MagicMock()
    return PipelineContext(
        run_id=deterministic_uuid_from_callsite("test_record_normalization_core"),
        run_type=RunType.INCREMENTAL,
        logger=logger,
    )


def test_normalize_record_applies_identifier_date_json_and_hash_rules() -> None:
    processor = build_normalization_processor(provider="crossref")
    record = {
        "entity_id": "crossref:raw",
        "content_hash": "stale",
        "publication_doi": " HTTPS://doi.org/10.1000/ABC ",
        "publication_pmid": 12345,
        "publication_date": "2024-02",
        "title": "  Example <b>Title</b>  ",
        "payload": {"b": 1, "a": [2, 1]},
        "_run_id": "keep-me",
    }

    normalized = processor.normalize_record(record)

    assert normalized["entity_id"] == "crossref:raw"
    assert normalized["_run_id"] == "keep-me"
    assert normalized["publication_doi"] == "10.1000/abc"
    assert normalized["publication_pmid"] == "12345"
    assert normalized["publication_date"] == "2024-02-29"
    assert normalized["title"] == "Example Title"
    assert normalized["payload"] == '{"a":[2,1],"b":1}'
    assert normalized["content_hash"] == str(
        generate_content_hash(
            normalized,
            "crossref",
            exclude_none=True,
            exclude_fields={"entity_id", "content_hash"},
        )
    )


def test_finalize_pre_silver_record_helper_orchestrates_the_finalization_seam() -> None:
    pre_silver = PreSilverRecord(
        entity_id="entity:1",
        business_data={"raw": " value "},
        build_silver_record=lambda _context, entity_id, content_hash, index, business: {
            "entity_id": entity_id,
            "content_hash": content_hash,
            "index": index,
            **business,
        },
    )

    silver_record = finalize_pre_silver_record(
        _PreSilverFinalizerHarness(),
        pre_silver,
        context=cast("PipelineContext", object()),
        index=3,
    )

    assert silver_record == {
        "entity_id": "entity:1",
        "content_hash": "hash:value",
        "index": 3,
        "normalized": "value",
        "projected_index": 3,
    }


def test_compute_content_hash_is_idempotent_for_normalized_payload() -> None:
    processor = build_normalization_processor(provider="crossref")
    normalized_payload = {
        "entity_id": "crossref:1",
        "content_hash": "stale",
        "title": "Example Title",
        "payload": '{"a":1,"b":2}',
        "_run_id": "keep-me",
    }

    first_hash = processor.compute_content_hash(normalized_payload)
    second_hash = processor.compute_content_hash(normalized_payload)

    assert first_hash == second_hash


def test_normalize_record_leaves_invalid_json_like_strings_as_trimmed_text() -> None:
    processor = build_normalization_processor(provider="crossref")

    normalized = processor.normalize_record(
        {"entity_id": "crossref:1", "content_hash": "stale", "raw_json": "{not json}"}
    )

    assert normalized["raw_json"] == "{not json}"


@pytest.mark.unit
def test_normalize_business_data_serializes_crossref_issn_collection_to_canonical_json() -> (
    None
):
    processor = build_normalization_processor(
        provider="crossref", entity_type="publication"
    )

    normalized = processor.normalize_business_data(
        {
            "issn": " ISSN:1234567X ",
            "issn_list": ["2049-3630", "ISSN:1234567X"],
        }
    )

    assert normalized["issn"] == "1234-567X"
    assert normalized["issn_list"] == '["1234-567X","2049-3630"]'
    assert not isinstance(normalized["issn_list"], list)


@pytest.mark.unit
def test_compute_content_hashes_by_version_returns_ordered_multi_hash_payload() -> None:
    processor = build_normalization_processor(
        provider="crossref",
        content_hash_policy_by_version=ContentHashPolicyByVersion(
            active_version="2.0.0",
            affects_hash=True,
            policies=(
                ContentHashVersionPolicy(
                    version="1.0.0",
                    include_fields=frozenset({"title"}),
                    exclude_fields=frozenset(),
                ),
                ContentHashVersionPolicy(
                    version="2.0.0",
                    include_fields=frozenset({"title", "journal"}),
                    exclude_fields=frozenset(),
                ),
            ),
        ),
    )

    payload = {"entity_id": "crossref:1", "title": "Example", "journal": "Nature"}

    hashes = processor.compute_content_hashes_by_version(payload)

    assert tuple(hashes) == ("1.0.0", "2.0.0")
    assert hashes["1.0.0"] != hashes["2.0.0"]


@pytest.mark.unit
def test_profile_backed_hash_policy_fails_closed_for_unknown_include_fields() -> None:
    processor = build_normalization_processor(
        provider="chembl",
        entity_type="activity",
        content_hash_policy_by_version=ContentHashPolicyByVersion(
            active_version="1.0.0",
            policies=(
                ContentHashVersionPolicy(
                    version="1.0.0",
                    include_fields=frozenset({"activity_chembl_id"}),
                    exclude_fields=frozenset(),
                ),
            ),
        ),
    )

    with pytest.raises(ValueError, match="activity_chembl_id"):
        processor.compute_content_hash({"activity_id": "CHEMBL1"})


@pytest.mark.unit
def test_profile_backed_hash_policy_fails_closed_for_unknown_exclude_fields() -> None:
    processor = build_normalization_processor(
        provider="chembl",
        entity_type="activity",
        content_hash_policy_by_version=ContentHashPolicyByVersion(
            active_version="1.0.0",
            policies=(
                ContentHashVersionPolicy(
                    version="1.0.0",
                    include_fields=frozenset({"activity_id"}),
                    exclude_fields=frozenset({"document_chembl_id"}),
                ),
            ),
        ),
    )

    with pytest.raises(ValueError, match="document_chembl_id"):
        processor.compute_content_hash({"activity_id": "CHEMBL1"})


@pytest.mark.unit
def test_profile_backed_hash_policy_allows_explicit_technical_exclusions() -> None:
    processor = build_normalization_processor(
        provider="chembl",
        entity_type="activity",
        content_hash_policy_by_version=ContentHashPolicyByVersion(
            active_version="1.0.0",
            policies=(
                ContentHashVersionPolicy(
                    version="1.0.0",
                    include_fields=frozenset({"activity_id"}),
                    exclude_fields=frozenset({"entity_id", "_future_runtime_field"}),
                ),
            ),
        ),
    )

    assert processor.compute_content_hash({"activity_id": "CHEMBL1"})


@pytest.mark.unit
def test_authoritative_config_hash_policy_overrides_profile_field_selection() -> None:
    processor = build_normalization_processor(
        provider="chembl",
        entity_type="activity",
        content_hash_policy_authoritative=True,
        content_hash_include_fields=frozenset({"activity_id"}),
        content_hash_exclude_fields=frozenset(),
    )

    hash_a = processor.compute_content_hash(
        {"activity_id": "CHEMBL1", "value": "10", "relation": "="}
    )
    hash_b = processor.compute_content_hash(
        {"activity_id": "CHEMBL1", "value": "20", "relation": "<"}
    )

    assert hash_a == hash_b


@pytest.mark.unit
def test_profile_backed_activity_companion_fields_recompute_from_normalized_context() -> (
    None
):
    processor = build_normalization_processor(provider="chembl", entity_type="activity")

    normalized = processor.normalize_business_data(
        {
            "activity_id": "12345",
            "molecule_id": "CHEMBL25",
            "bao_endpoint": " bao:0000190 ",
            "bao_format": "bao:0000218",
            "uo_units": "uo:0000065",
            "qudt_units": " https://qudt.org/vocab/unit/NanoMOL-PER-L ",
            "bao_endpoint_iri": None,
            "bao_endpoint_mapping_status": None,
            "bao_format_iri": None,
            "bao_format_mapping_status": None,
            "bao_ontology_version": None,
            "uo_unit_iri": None,
            "uo_unit_mapping_status": None,
            "uo_ontology_version": None,
            "qudt_unit_iri": None,
            "qudt_unit_mapping_status": None,
            "qudt_ontology_version": None,
        }
    )

    assert normalized["bao_endpoint"] == "BAO_0000190"
    assert (
        normalized["bao_endpoint_iri"] == "https://purl.obolibrary.org/obo/BAO_0000190"
    )
    assert normalized["bao_endpoint_mapping_status"] == "mapped"
    assert normalized["uo_unit_iri"] == "https://purl.obolibrary.org/obo/UO_0000065"
    assert normalized["uo_unit_mapping_status"] == "mapped"
    assert normalized["qudt_unit_iri"] == "https://qudt.org/vocab/unit/NanoMOL-PER-L"
    assert normalized["qudt_unit_mapping_status"] == "mapped"


@pytest.mark.unit
def test_profile_backed_publication_taxonomy_fields_recompute_from_raw_provider_type(
    publication_type_classification_data: None,
) -> None:
    processor = build_normalization_processor(
        provider="chembl",
        entity_type="publication",
    )

    normalized = processor.normalize_business_data(
        {
            "publication_id": "CHEMBL1234567",
            "publication_type_raw": "PUBLICATION",
            "publication_type": None,
            "publication_type_unified": None,
            "publication_subclass": None,
            "publication_class": None,
        }
    )

    assert normalized["publication_type_raw"] == "PUBLICATION"
    assert normalized["publication_type"] == "journal-article"
    assert normalized["publication_type_unified"] == "Journal Article"
    assert normalized["publication_subclass"] == "Original Experimental Data"
    assert normalized["publication_class"] == "EXP"


@pytest.mark.unit
def test_profile_backed_target_organism_class_recomputes_from_normalized_siblings() -> (
    None
):
    processor = build_normalization_processor(provider="chembl", entity_type="target")

    normalized = processor.normalize_business_data(
        {
            "target_id": "CHEMBL1862",
            "organism": "Homo sapiens",
            "taxonomy_id": 9606,
            "organism_class": None,
        }
    )

    assert normalized["organism"] == "Homo sapiens"
    assert normalized["organism_class"] == "multicellular"


@pytest.mark.unit
def test_finalize_pre_silver_attaches_active_and_versioned_content_hashes() -> None:
    processor = build_normalization_processor(
        provider="crossref",
        content_hash_policy_by_version=ContentHashPolicyByVersion(
            active_version="2.0.0",
            affects_hash=True,
            policies=(
                ContentHashVersionPolicy(
                    version="1.0.0",
                    include_fields=frozenset({"title"}),
                    exclude_fields=frozenset(),
                ),
                ContentHashVersionPolicy(
                    version="2.0.0",
                    include_fields=frozenset({"title", "journal"}),
                    exclude_fields=frozenset(),
                ),
            ),
        ),
    )
    pre_silver = PreSilverRecord(
        entity_id="crossref:1",
        business_data={"title": "Example", "journal": "Nature"},
        build_silver_record=lambda _context, entity_id, content_hash, index, business: {
            "entity_id": entity_id,
            "content_hash": content_hash,
            "_index": index,
            **business,
        },
    )

    silver_record = processor.finalize_pre_silver(
        pre_silver,
        context=cast("PipelineContext", object()),
        index=0,
    )

    assert silver_record is not None
    assert (
        silver_record["content_hash"]
        == silver_record["_content_hashes_by_version"]["2.0.0"]
    )
    assert (
        silver_record["_content_hashes_by_version"]["1.0.0"]
        != silver_record["content_hash"]
    )


@pytest.mark.unit
def test_finalize_pre_silver_skips_versioned_hash_projection_when_rollout_does_not_affect_hash() -> (
    None
):
    processor = build_normalization_processor(
        provider="crossref",
        content_hash_policy_by_version=ContentHashPolicyByVersion(
            active_version="2.0.0",
            affects_hash=False,
            policies=(
                ContentHashVersionPolicy(
                    version="1.0.0",
                    include_fields=frozenset({"title"}),
                    exclude_fields=frozenset(),
                ),
                ContentHashVersionPolicy(
                    version="2.0.0",
                    include_fields=frozenset({"title", "journal"}),
                    exclude_fields=frozenset(),
                ),
            ),
        ),
    )
    pre_silver = PreSilverRecord(
        entity_id="crossref:1",
        business_data={"title": "Example", "journal": "Nature"},
        build_silver_record=lambda _context, entity_id, content_hash, index, business: {
            "entity_id": entity_id,
            "content_hash": content_hash,
            "_index": index,
            **business,
        },
    )

    silver_record = processor.finalize_pre_silver(
        pre_silver,
        context=cast("PipelineContext", object()),
        index=0,
    )

    assert silver_record is not None
    assert "_content_hashes_by_version" not in silver_record


@pytest.mark.unit
def test_finalize_pre_silver_cannot_reject_on_semantic_silver_filter() -> None:
    transformer = _PreSilverFilterTransformer(
        provider="crossref",
        silver_filters=SilverFilterConfig(
            column_filters=(
                GoldColumnFilter(
                    column="status",
                    values=frozenset({"allowed"}),
                ),
            ),
        ),
        dependencies=build_test_transformer_dependencies(),
    )
    pre_silver = PreSilverRecord(
        entity_id="crossref:1",
        business_data={"status": "blocked-by-semantic-filter"},
        build_silver_record=lambda _context, entity_id, content_hash, index, business: {
            "entity_id": entity_id,
            "content_hash": content_hash,
            "_index": index,
            **business,
        },
        apply_silver_filter=transformer._apply_pre_silver_filter,
    )

    silver_record = build_normalization_processor(
        provider="crossref"
    ).finalize_pre_silver(
        pre_silver,
        context=_pipeline_context(),
        index=0,
    )

    assert silver_record is not None
    assert silver_record["status"] == "blocked-by-semantic-filter"
