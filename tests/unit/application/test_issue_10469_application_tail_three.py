"""Behavioral coverage for small application branch tails in #10469."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from bioetl.application.core.base_transformer import _structural_policy_contracts
from bioetl.application.core.base_transformer._structural_policy_support import (
    NoOpStructuralPolicy,
    build_structural_policy,
)
from bioetl.application.core.batch_transformer_quarantine import (
    route_single_transform_attempt,
)
from bioetl.application.core.batch_transformer_state import RecordTransformOutcome
from bioetl.application.core.batch_transformer_streaming import StreamingBatchProcessor
from bioetl.application.core.data_source_mixins import _WrappedDataSourceDelegationMixin
from bioetl.application.core.publication_term_filtering_mixin import (
    PublicationTermFilteringMixin,
)
from bioetl.application.pipelines.chembl import subcellular_fraction_transformer
from bioetl.application.pipelines.chembl.publication_term_transformer import (
    PublicationTermTransformer,
)
from bioetl.application.pipelines.chembl.target_helpers import XrefHelper
from bioetl.application.pipelines.crossref.blocks import _CrossRefCoreBlock
from bioetl.application.pipelines.crossref.extractors import extract_affiliations
from bioetl.application.pipelines.pubmed._block_definitions_base import _PubMedXmlBlock
from bioetl.application.pipelines.pubmed._block_definitions_edition import (
    _PubMedJournalBlock,
)
from bioetl.application.pipelines.pubmed._block_definitions_identifiers import (
    _PubMedIdentifierBlock,
)
from bioetl.application.pipelines.pubmed.extractors.author import AuthorExtractor
from bioetl.application.pipelines.uniprot.extractors import _comment_facets_all
from bioetl.application.pipelines.uniprot.extractors._comment_helpers import (
    _extract_isoform_synonym_values,
)

pytestmark = pytest.mark.unit


def test_structural_policy_falls_back_when_schema_has_no_contracts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        _structural_policy_contracts,
        "resolve_pandera_schema",
        lambda _schema: object(),
    )
    monkeypatch.setattr(
        _structural_policy_contracts,
        "resolve_field_contracts",
        lambda **_kwargs: (),
    )

    policy = build_structural_policy(
        domain_config=SimpleNamespace(), pandera_silver_schema=object()
    )

    assert isinstance(policy, NoOpStructuralPolicy)
    assert policy.apply({"id": "x"}).record == {"id": "x"}


@pytest.mark.asyncio
async def test_single_transform_attempt_without_records_is_not_quarantined() -> None:
    result = await route_single_transform_attempt(
        context=SimpleNamespace(),
        quarantine_manager=SimpleNamespace(),
        attempt=RecordTransformOutcome(silver_record=None, gold_record=None),
        batch_id="batch-1",
    )

    assert result.silver_record is None
    assert result.is_quarantined is False
    assert result.is_filtered_out is False


@pytest.mark.asyncio
async def test_streaming_processor_clamps_monitor_recommendation_to_one() -> None:
    transformer = SimpleNamespace(transform_stream=AsyncMock(side_effect=["a", "b"]))
    monitor = SimpleNamespace(get_recommended_batch_size=lambda _current: 0)
    processor = StreamingBatchProcessor(transformer, monitor)

    results = [
        result
        async for result in processor.process_in_chunks(
            [{"id": 1}, {"id": 2}], "batch-1", chunk_size=2
        )
    ]

    assert results == ["a", "b"]
    assert [call.args[0] for call in transformer.transform_stream.await_args_list] == [
        [{"id": 1}],
        [{"id": 2}],
    ]


@pytest.mark.asyncio
async def test_wrapped_data_source_rejects_invalid_enhanced_health_result() -> None:
    class Wrapper(_WrappedDataSourceDelegationMixin):
        def __init__(self) -> None:
            self._data_source = SimpleNamespace(
                check_health=AsyncMock(return_value="ok")
            )

        def _after_wrapped_data_source_enter(self) -> None:
            return None

    with pytest.raises(TypeError, match="must return HealthCheckResult"):
        await Wrapper().check_health()


@pytest.mark.asyncio
async def test_publication_term_multi_filter_zero_limit_yields_nothing() -> None:
    class Host(PublicationTermFilteringMixin):
        PUBLICATION_LIMIT_MULTIPLIER = 2
        SOURCE_ENTITY_TYPE = "publication"

    filterable = SimpleNamespace(fetch_multi_filtered=Mock())

    records = [
        record
        async for record in Host()._fetch_target_multi_filtered_records(
            filterable, {"target_id": ["T1"]}, limit=0
        )
    ]

    assert records == []
    filterable.fetch_multi_filtered.assert_not_called()


def test_publication_term_transformer_returns_first_extracted_term() -> None:
    transformer = object.__new__(PublicationTermTransformer)
    transformer.extract_terms_from_document = Mock(
        return_value=[{"term": "first"}, {"term": "second"}]
    )

    result = transformer._extract_business_data(
        {"publication_id": "CHEMBL1"}, "CHEMBL1"
    )

    assert result == {"term": "first"}


@pytest.mark.asyncio
async def test_subcellular_fraction_returns_none_for_unresolvable_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transformer = object.__new__(
        subcellular_fraction_transformer.SubcellularFractionTransformer
    )
    monkeypatch.setattr(
        subcellular_fraction_transformer,
        "_resolve_subcellular_fraction_payload",
        lambda *_args: None,
    )

    assert await transformer.transform_pre_silver(SimpleNamespace(), {}, 0) is None


def test_xref_projection_skips_non_mapping_entries() -> None:
    result = XrefHelper.project_component_xrefs(
        ["invalid", {"xref_src_db": "UniProt", "xref_id": "P12345"}]
    )

    assert result["target_xref_uniprot_ids"] == "P12345"


def test_crossref_core_block_requires_prevalidated_doi() -> None:
    block = _CrossRefCoreBlock(
        validate_doi=lambda _value: None,
        classify_pub_type=lambda _value: {},
        serialize_json_list=lambda _value: None,
    )

    with pytest.raises(ValueError, match="DOI should be validated"):
        block.extract({"DOI": "not-a-doi"})


def test_crossref_affiliations_skip_non_list_payloads() -> None:
    result = extract_affiliations(
        {
            "author": [
                {"affiliation": "invalid"},
                {"affiliation": [{"name": "Institute A"}]},
            ]
        }
    )

    assert result == ["Institute A"]


def test_pubmed_xml_block_resolves_empty_context_without_root() -> None:
    block = _PubMedXmlBlock(lambda: None)

    assert block._resolve_article_context() == (None, None, None)


def test_pubmed_journal_block_emits_empty_medline_fields() -> None:
    block = _PubMedJournalBlock(
        serialize_json_list=lambda _value: None,
        root_resolver=lambda: None,
    )

    assert block._build_medline_fields(None) == {
        "nlm_unique_id": None,
        "citation_subset": None,
        "country": None,
    }


def test_pubmed_identifier_block_emits_null_pmid_without_root() -> None:
    block = _PubMedIdentifierBlock(
        data_normalizer=SimpleNamespace(), root_resolver=lambda: None
    )

    assert block.extract({}) == {"pmid": None}


def test_pubmed_author_extractor_skips_blank_affiliation() -> None:
    author = ET.fromstring(
        "<Author><AffiliationInfo><Affiliation /></AffiliationInfo></Author>"
    )

    affiliations, structured = AuthorExtractor()._extract_affiliations(author)

    assert affiliations == []
    assert structured == []


def test_uniprot_comment_serialization_ignores_scalar_facets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        _comment_facets_all,
        "extract_all_comments_raw",
        lambda _comments: dict.fromkeys(
            _comment_facets_all._COMMENT_OUTPUT_KEYS, "invalid"
        ),
    )

    result = _comment_facets_all.extract_all_comments(None)

    assert all(result[key] is None for key in _comment_facets_all._COMMENT_OUTPUT_KEYS)


def test_uniprot_isoform_synonyms_reject_non_list_payload() -> None:
    assert _extract_isoform_synonym_values({"synonyms": "invalid"}) == []
