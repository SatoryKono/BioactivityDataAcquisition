"""Behavior-focused unit tests for #10518 (application pipelines, part B).

Covers residual lines in uniprot comment-facet extractors, publication
transformer context/records helpers, pubmed classification extractor,
semanticscholar author extractors, the chembl publication transformer, and
openalex author extractors.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock
from xml.etree.ElementTree import Element, SubElement, fromstring

import pytest

from tests.helpers.transformer_dependencies import build_test_transformer_dependencies

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# uniprot/extractors/_comment_facets_extractors.py
# ---------------------------------------------------------------------------

from bioetl.application.pipelines.uniprot.extractors._comment_facets_extractors import (
    count_isoforms,
    extract_alternative_products,
    extract_biophysicochemical_properties,
    extract_by_type,
    extract_catalytic_activity,
    extract_cofactors,
    extract_isoform_details,
    extract_reaction_ec_numbers,
    extract_reactions,
    extract_subcellular_locations,
    extract_text_values,
)


class TestCommentFacetsDegenerate:
    def test_none_inputs(self) -> None:
        assert extract_text_values(None, "FUNCTION") == []  # type: ignore[arg-type]
        assert extract_by_type(None, "FUNCTION") is None
        assert extract_catalytic_activity(None) is None
        assert extract_subcellular_locations(None) is None
        assert extract_alternative_products(None) is None
        assert count_isoforms(None) is None
        assert extract_cofactors(None) is None
        assert extract_biophysicochemical_properties(None) is None
        assert extract_reactions(None) is None
        assert extract_reaction_ec_numbers(None) is None

    def test_empty_inputs(self) -> None:
        assert extract_text_values([], "FUNCTION") == []
        assert extract_by_type([], "FUNCTION") is None
        assert extract_catalytic_activity([]) is None
        assert extract_subcellular_locations([]) is None
        assert extract_alternative_products([]) is None
        assert count_isoforms([]) is None
        assert extract_cofactors([]) is None
        assert extract_biophysicochemical_properties([]) is None
        assert extract_reactions([]) is None
        assert extract_reaction_ec_numbers([]) is None

    def test_unindexed_shapes_yield_none(self) -> None:
        comments = [{"no_comment_type": True}]
        assert extract_by_type(comments, "FUNCTION") is None
        assert extract_catalytic_activity(comments) is None
        assert extract_subcellular_locations(comments) is None
        assert extract_alternative_products(comments) is None
        assert extract_cofactors(comments) is None
        assert extract_biophysicochemical_properties(comments) is None
        assert extract_reactions(comments) is None
        assert extract_reaction_ec_numbers(comments) is None
        assert extract_text_values(comments, "FUNCTION") == []

    def test_isoform_details_degenerate(self) -> None:
        details = extract_isoform_details(None)
        assert isinstance(details, dict)
        assert details and all(value is None for value in details.values())
        empty_details = extract_isoform_details([])
        assert isinstance(empty_details, dict)
        assert empty_details and all(value is None for value in empty_details.values())

    def test_isoform_paths_with_unindexed_comments(self) -> None:
        comments = [{"no_comment_type": True}]
        assert count_isoforms(comments) is None or isinstance(
            count_isoforms(comments), int
        )
        details = extract_isoform_details(comments)
        assert isinstance(details, dict)
        assert details and all(value is None for value in details.values())

    def test_text_values_positive(self) -> None:
        comments = [
            {
                "commentType": "FUNCTION",
                "texts": [{"value": "catalyzes X"}, {"value": ""}],
            },
            {"commentType": "OTHER", "texts": [{"value": "zzz"}]},
        ]
        assert extract_text_values(comments, "FUNCTION") == ["catalyzes X"]
        assert extract_text_values(comments, "MISSING") == []


# ---------------------------------------------------------------------------
# common/publication_transformer_context.py
# ---------------------------------------------------------------------------

from bioetl.application.pipelines.common.publication_transformer_context import (
    BasePublicationTransformerContext,
    build_runtime_publication_transformer_init,
    coerce_publication_transformer_init,
    publication_transformer_kwargs,
)


class TestCoercePublicationTransformerInit:
    def test_context_passthrough(self) -> None:
        ctx = BasePublicationTransformerContext(provider="pubmed")
        assert coerce_publication_transformer_init(ctx) is ctx

    def test_context_with_explicit_args_raises(self) -> None:
        ctx = BasePublicationTransformerContext(provider="pubmed")
        with pytest.raises(TypeError, match="unexpected explicit arguments"):
            coerce_publication_transformer_init(ctx, tracer=MagicMock())

    def test_context_with_none_fields_ok(self) -> None:
        ctx = BasePublicationTransformerContext(provider="pubmed")
        assert coerce_publication_transformer_init(ctx, tracer=None) is ctx

    def test_string_init_uses_default_entity_type(self) -> None:
        ctx = coerce_publication_transformer_init("crossref")
        assert ctx.provider == "crossref"
        assert ctx.entity_type == "publication"

    def test_fields_provider_and_di_passthrough(self) -> None:
        tracer = MagicMock()
        ctx = coerce_publication_transformer_init(
            None,
            provider="openalex",
            entity_type="work",
            tracer=tracer,
            record_normalizer=MagicMock(),
        )
        assert ctx.provider == "openalex"
        assert ctx.entity_type == "work"
        assert ctx.tracer is tracer

    def test_default_provider_fallback(self) -> None:
        ctx = coerce_publication_transformer_init(
            None, default_provider="semanticscholar"
        )
        assert ctx.provider == "semanticscholar"

    def test_missing_provider_raises(self) -> None:
        with pytest.raises(TypeError, match="requires a provider string"):
            coerce_publication_transformer_init(None)
        with pytest.raises(TypeError, match="requires a provider string"):
            coerce_publication_transformer_init(None, provider="")

    def test_transformer_kwargs_passthrough(self) -> None:
        init_locals = {
            "entity_type": "publication",
            "silver_filters": None,
            "gold_filters": None,
            "tracer": None,
            "metrics": None,
            "identity_service": None,
            "pii_hasher": None,
            "dependencies": None,
            "provider": "pubmed",
            "self": None,
        }
        assert publication_transformer_kwargs(init_locals) == dict.fromkeys(
            (
                "entity_type",
                "silver_filters",
                "gold_filters",
                "tracer",
                "metrics",
                "identity_service",
                "pii_hasher",
                "dependencies",
            )
        ) | {"entity_type": "publication"}

    def test_build_runtime_init(self) -> None:
        runtime_init = build_runtime_publication_transformer_init(
            default_provider="pubmed"
        )
        assert callable(runtime_init)
        assert (
            runtime_init.__doc__
            == "Shared runtime-generated publication transformer constructor."
        )


# ---------------------------------------------------------------------------
# common/publication_transformer_records.py
# ---------------------------------------------------------------------------

import bioetl.application.pipelines.common.publication_transformer_records as pub_records
from bioetl.application.pipelines.common.publication_transformer_records import (
    assemble_publication_silver_record,
    build_pre_silver_publication_record,
    classification_payload,
    compute_publication_identifiers,
    prepare_content_hash_payload,
    resolve_publication_entity_id,
)


def _mock_transformer() -> MagicMock:
    transformer = MagicMock()
    transformer.compute_entity_id = MagicMock(return_value="ENTITY-1")
    transformer.compute_content_hash = MagicMock(return_value="HASH-1")
    transformer._apply_structural_policy = MagicMock(
        side_effect=lambda context, record, index: record
    )
    transformer._apply_silver_filter = MagicMock(return_value=None)
    transformer._record_normalizer = MagicMock()
    transformer._record_normalizer.project_normalization_findings = MagicMock(
        side_effect=lambda record, context, index: record
    )
    return transformer


class TestPublicationRecords:
    def test_classification_payload(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            pub_records,
            "build_publication_type_classification_payload",
            lambda provider, **kwargs: {"publication_type": kwargs.get("raw_type")},
        )
        out = classification_payload("crossref", "journal-article", None)
        assert out == {"publication_type": "journal-article"}

    def test_resolve_entity_id(self) -> None:
        transformer = _mock_transformer()
        assert resolve_publication_entity_id(transformer, "doi", "10.1/x") == "ENTITY-1"
        transformer.compute_entity_id.assert_called_once_with(
            source_id="10.1/x", record={"doi": "10.1/x"}
        )

    def test_prepare_content_hash_payload(self) -> None:
        assert prepare_content_hash_payload({"a": 1, "_source": "x", "_dq": 1}) == {
            "a": 1
        }

    def test_compute_identifiers(self) -> None:
        transformer = _mock_transformer()
        entity_id, content_hash = compute_publication_identifiers(
            transformer, "doi", "10.1/x", {"title": "t", "_source": "s"}
        )
        assert (entity_id, content_hash) == ("ENTITY-1", "HASH-1")
        transformer.compute_content_hash.assert_called_once_with(
            {"title": "t"}, exclude_none=True
        )

    def test_build_pre_silver_record_callbacks(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            pub_records,
            "build_publication_silver_record",
            lambda *args: {"built": True},
        )
        transformer = _mock_transformer()
        prepared = SimpleNamespace(
            primary_id_field="doi", primary_id="10.1/x", business_data={"title": "t"}
        )
        staged = build_pre_silver_publication_record(transformer, prepared)  # type: ignore[arg-type]
        assert staged.entity_id == "ENTITY-1"
        assert staged.business_data == {"title": "t"}
        context = MagicMock()
        assert staged.build_silver_record(context, "E", "H", 0, {"title": "t"}) == {
            "built": True
        }
        record: dict[str, object] = {"title": "t"}
        assert staged.apply_structural_policy is not None
        assert staged.apply_structural_policy(context, record, 0) == {"title": "t"}  # type: ignore[misc]
        assert staged.apply_silver_filter is not None
        assert staged.apply_silver_filter(context, record, 0) is None  # type: ignore[misc]

    def test_assemble_silver_record(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            pub_records,
            "build_publication_silver_record",
            lambda *args: {"silver": True},
        )
        transformer = _mock_transformer()
        prepared = SimpleNamespace(
            primary_id_field="doi", primary_id="10.1/x", business_data={"title": "t"}
        )
        out = assemble_publication_silver_record(
            transformer,  # type: ignore[arg-type]
            MagicMock(),  # type: ignore[arg-type]
            index=0,
            prepared=prepared,  # type: ignore[arg-type]
            normalized_business_data={"title": "t"},
        )
        assert out == {"silver": True}


# ---------------------------------------------------------------------------
# pubmed/extractors/classification.py
# ---------------------------------------------------------------------------

from bioetl.application.pipelines.pubmed.extractors.classification import (
    ClassificationExtractor,
)


def _pubmed_article_xml() -> Element:
    root = fromstring(
        "<PubmedArticle><MedlineCitation><Article></Article></MedlineCitation></PubmedArticle>"
    )
    medline = root.find(".//MedlineCitation")
    assert medline is not None
    keyword_list = SubElement(medline, "KeywordList")
    for text in ("  kinase ", "", None, "inhibitor"):
        node = SubElement(keyword_list, "Keyword")
        node.text = text  # type: ignore[assignment]
    mesh_list = SubElement(medline, "MeshHeadingList")
    heading = SubElement(mesh_list, "MeshHeading")
    descriptor = SubElement(heading, "DescriptorName")
    descriptor.text = "Neoplasms"
    empty_heading = SubElement(mesh_list, "MeshHeading")
    SubElement(empty_heading, "QualifierName")
    article = root.find(".//Article")
    assert article is not None
    type_list = SubElement(article, "PublicationTypeList")
    for text in ("Journal Article", "  "):
        node = SubElement(type_list, "PublicationType")
        node.text = text
    return root


class TestPubmedClassificationExtractor:
    def test_extract_none__pipelines_b_1(self) -> None:
        assert ClassificationExtractor().extract(None) is None

    def test_extract_empty_shapes(self) -> None:
        raw = ClassificationExtractor().extract(fromstring("<PubmedArticle/>"))
        assert raw == {"keywords": [], "mesh_terms": [], "publication_types": []}

    def test_extract_full(self) -> None:
        raw = ClassificationExtractor().extract(_pubmed_article_xml())
        assert raw is not None
        assert raw["keywords"] == ["  kinase ", "", None, "inhibitor"]
        assert raw["mesh_terms"] == ["Neoplasms"]
        assert raw["publication_types"] == ["Journal Article", "  "]

    def test_normalize(self) -> None:
        normalized = ClassificationExtractor().normalize(
            {
                "keywords": [" a ", "", None],
                "mesh_terms": [" b "],
                "publication_types": ["  ", "c"],
            }
        )
        assert normalized == {
            "keywords": ["a"],
            "mesh_terms": ["b"],
            "publication_types": ["c"],
        }

    def test_pub_types_missing_list(self) -> None:
        extractor = ClassificationExtractor()
        assert extractor._extract_pub_types_raw(None) == []
        article = fromstring("<Article/>")
        assert extractor._extract_pub_types_raw(article) == []

    def test_keywords_and_mesh_missing_lists(self) -> None:
        extractor = ClassificationExtractor()
        assert extractor._extract_keywords_raw(None) == []
        assert extractor._extract_mesh_raw(None) == []
        medline = fromstring("<MedlineCitation/>")
        assert extractor._extract_keywords_raw(medline) == []
        assert extractor._extract_mesh_raw(medline) == []

    def test_parse_helpers(self) -> None:
        medline = _pubmed_article_xml().find(".//MedlineCitation")
        assert ClassificationExtractor.parse_keywords(medline) == [
            "kinase",
            "inhibitor",
        ]
        assert ClassificationExtractor.parse_mesh_terms(medline) == ["Neoplasms"]
        assert ClassificationExtractor.parse_keywords(None) == []
        assert ClassificationExtractor.parse_mesh_terms(None) == []
        article = _pubmed_article_xml().find(".//Article")
        assert article is not None
        assert ClassificationExtractor.parse_publication_types(article) == [
            "Journal Article"
        ]

    def test_parse_chemicals(self) -> None:
        medline = fromstring(
            "<MedlineCitation><ChemicalList>"
            "<Chemical><NameOfSubstance>Aspirin</NameOfSubstance></Chemical>"
            "<Chemical><NameOfSubstance>  </NameOfSubstance></Chemical>"
            "<Chemical></Chemical>"
            "</ChemicalList></MedlineCitation>"
        )
        assert ClassificationExtractor.parse_chemicals(medline) == ["Aspirin"]
        assert ClassificationExtractor.parse_chemicals(None) == []
        assert (
            ClassificationExtractor.parse_chemicals(fromstring("<MedlineCitation/>"))
            == []
        )

    def test_parse_gene_symbols(self) -> None:
        medline = fromstring(
            "<MedlineCitation><GeneSymbolList>"
            "<GeneSymbol>TP53</GeneSymbol><GeneSymbol>  BRCA1 </GeneSymbol>"
            "<GeneSymbol></GeneSymbol>"
            "</GeneSymbolList></MedlineCitation>"
        )
        assert ClassificationExtractor.parse_gene_symbols(medline) == ["TP53", "BRCA1"]
        assert ClassificationExtractor.parse_gene_symbols(None) == []
        assert (
            ClassificationExtractor.parse_gene_symbols(fromstring("<MedlineCitation/>"))
            == []
        )

    def test_parse_databanks(self) -> None:
        medline = fromstring(
            "<MedlineCitation><DataBankList>"
            "<DataBank><DataBankName>ClinicalTrials.gov</DataBankName>"
            "<AccessionNumberList><AccessionNumber> NCT123 </AccessionNumber>"
            "<AccessionNumber></AccessionNumber><AccessionNumber>   </AccessionNumber>"
            "</AccessionNumberList></DataBank>"
            "<DataBank><AccessionNumberList><AccessionNumber>X</AccessionNumber></AccessionNumberList></DataBank>"
            "</DataBankList></MedlineCitation>"
        )
        assert ClassificationExtractor.parse_databanks(medline) == [
            {"databank_name": "ClinicalTrials.gov", "accession_numbers": ["NCT123"]}
        ]
        assert ClassificationExtractor.parse_databanks(None) == []
        assert (
            ClassificationExtractor.parse_databanks(fromstring("<MedlineCitation/>"))
            == []
        )


# ---------------------------------------------------------------------------
# semanticscholar/_author_extractors.py
# ---------------------------------------------------------------------------

from bioetl.application.pipelines.semanticscholar._author_extractors import (
    extract_affiliations,
    extract_author_h_indices,
    extract_author_ids,
    extract_author_orcids,
    extract_author_s2_ids,
    extract_authors,
)


class TestSemanticScholarAuthors:
    def test_extract_authors__pipelines_b_1(self) -> None:
        assert extract_authors(None) == []
        assert extract_authors([]) == []
        assert extract_authors(
            [{"name": " John "}, {"name": "  "}, {"name": ""}, {"name": None}, {}]
        ) == ["John"]

    def test_extract_author_ids__pipelines_b_1(self) -> None:
        assert extract_author_ids(None) == []
        assert extract_author_ids([]) == []
        authors = [
            {"authorId": "123", "name": "A"},
            {"name": "B"},
            {"authorId": "", "name": "C"},
            {"authorId": 456},
        ]
        assert extract_author_ids(authors) == ["123", "456"]

    def test_extract_author_s2_ids(self) -> None:
        assert extract_author_s2_ids(None) == []
        authors = [
            {"authorId": " abc "},
            {"authorId": ""},
            {"authorId": None},
            {"authorId": 7},
        ]
        assert extract_author_s2_ids(authors) == ["abc"]

    def test_extract_author_orcids__pipelines_b_1(self) -> None:
        assert extract_author_orcids(None) == []
        authors = [
            {"name": "A", "externalIds": {"ORCID": " 0000-1 "}},
            {"name": "B", "externalIds": None},
            {"name": "C"},
            {"name": "D", "externalIds": {"ORCID": "  "}},
            {"name": "E", "externalIds": "nope"},
        ]
        assert extract_author_orcids(authors) == ["0000-1", "", "", "", ""]

    def test_extract_author_h_indices(self) -> None:
        assert extract_author_h_indices(None) == []
        authors = [{"hIndex": 5}, {"hIndex": None}, {"hIndex": -1}, {"hIndex": "x"}, {}]
        assert extract_author_h_indices(authors) == [5, None, None, None, None]

    def test_extract_affiliations(self) -> None:
        assert extract_affiliations(None) == []
        authors = [
            {"affiliations": ["Univ B", "Univ A", "Univ A", "  ", "", None, 5]},
            {"affiliations": "nope"},
            {},
        ]
        assert extract_affiliations(authors) == ["Univ A", "Univ B"]


# ---------------------------------------------------------------------------
# chembl/publication_transformer.py
# ---------------------------------------------------------------------------

from bioetl.application.pipelines.chembl.publication_transformer import (
    PublicationTransformer,
)
from bioetl.application.core.base_transformer import TransformationError


def _make_publication_transformer() -> PublicationTransformer:
    return PublicationTransformer(
        provider="chembl", dependencies=build_test_transformer_dependencies()
    )


class TestChemblPublicationTransformer:
    def test_resolve_primary_id_prefers_canonical(self) -> None:
        transformer = _make_publication_transformer()
        assert (
            transformer._resolve_primary_id({"publication_id": "CHEMBL1"}) == "CHEMBL1"
        )
        assert (
            transformer._resolve_primary_id({"document_chembl_id": "CHEMBL2"})
            == "CHEMBL2"
        )

    def test_resolve_primary_id_missing_raises(self) -> None:
        transformer = _make_publication_transformer()
        with pytest.raises(TransformationError):
            transformer._resolve_primary_id({})

    def test_extract_business_data_smoke(self) -> None:
        transformer = _make_publication_transformer()
        out = transformer._extract_business_data(
            {
                "publication_id": "CHEMBL1",
                "title": "T",
                "year": "2020",
                "citation_count": "4",
            },
            "CHEMBL1",
        )
        assert out["publication_id"] == "CHEMBL1"
        assert out["_source"] == "chembl"
        assert out["citations_received"] == 4

    def test_release_metadata_dict_branch(self) -> None:
        transformer = _make_publication_transformer()
        data: dict[str, object] = {}
        transformer._apply_release_metadata(
            data,  # type: ignore[arg-type]
            {"chembl_release": {"chembl_release": "35", "creation_date": "2024-01-01"}},  # type: ignore[dict-item]
        )
        assert data["chembl_release"] == "35"
        assert data["creation_date"] == "2024-01-01"

    def test_release_metadata_missing_branch(self) -> None:
        transformer = _make_publication_transformer()
        data: dict[str, object] = {}
        transformer._apply_release_metadata(data, {"publication_id": "CHEMBL1"})  # type: ignore[arg-type]
        assert data["chembl_release"] is None
        assert data["creation_date"] is None
        data2: dict[str, object] = {}
        transformer._apply_release_metadata(data2, {"chembl_release": "not-a-dict"})  # type: ignore[dict-item]
        assert data2["chembl_release"] is None

    def test_parse_citation_count(self) -> None:
        assert PublicationTransformer._parse_citation_count(None) is None
        assert PublicationTransformer._parse_citation_count("12") == 12
        assert PublicationTransformer._parse_citation_count(7) == 7
        assert PublicationTransformer._parse_citation_count("nope") is None
        assert PublicationTransformer._parse_citation_count(object()) is None


# ---------------------------------------------------------------------------
# openalex/_extractors_authors.py
# ---------------------------------------------------------------------------

from bioetl.application.pipelines.openalex._extractors_authors import (
    extract_affiliations as oa_affiliations,
    extract_author_ids as oa_author_ids,
    extract_author_orcids as oa_author_orcids,
    extract_authors as oa_authors,
    extract_institution_country_codes,
    extract_institution_ids,
    extract_institution_ror_ids,
)


class TestOpenAlexAuthors:
    def test_extract_authors__pipelines_b_2(self) -> None:
        authorships = [
            {"author": {"display_name": " Alice "}},
            {"author": "nope"},
            {"author": {"display_name": ""}},
            {"author": {"display_name": 5}},
            {},
        ]
        assert oa_authors(authorships) == ["Alice"]

    def test_extract_author_ids__pipelines_b_2(self) -> None:
        authorships = [
            {"author": {"id": "https://openalex.org/A1"}},
            {"author": "nope"},
            {"author": {}},
        ]
        assert oa_author_ids(authorships) == ["A1", "", ""]

    def test_extract_author_orcids__pipelines_b_2(self) -> None:
        authorships = [
            {"author": {"orcid": "https://orcid.org/0000-0001-2345-6789"}},
            {"author": "nope"},
            {"author": {}},
            {"author": {"orcid": None, "ormolecule_id": None}},
            {"author": {"orcid": "not-an-orcid"}},
        ]
        result = oa_author_orcids(authorships)
        assert result[0] == "0000-0001-2345-6789"
        assert result[1] == ""
        assert result[3] == ""
        assert result[4] == ""

    def test_extract_affiliations_shapes(self) -> None:
        authorships = [
            {"institutions": "nope"},
            {"institutions": ["x", None, {"display_name": "MIT"}, {}]},
            {},
        ]
        assert oa_affiliations(authorships) == ["MIT"]

    def test_extract_institution_ids(self) -> None:
        authorships = [
            {"institutions": [{"id": "https://openalex.org/I1"}, "junk", {"id": None}]},
            {"institutions": "nope"},
        ]
        assert extract_institution_ids(authorships) == ["I1"]

    def test_extract_country_codes(self) -> None:
        authorships = [
            {
                "institutions": [
                    {"country_code": "us"},
                    7,
                    {"country_code": ""},
                    {"country_code": None},
                ]
            },
            {"institutions": "nope"},
        ]
        assert extract_institution_country_codes(authorships) == ["US"]

    def test_extract_ror_ids(self) -> None:
        authorships = [
            {
                "institutions": [
                    {"ror": "https://ror.org/abc"},
                    {"ror": "http://other/x"},
                    {"ror": ""},
                    {"ror": None},
                    {"ror": 5},
                    "junk",
                ]
            },
            {"institutions": "nope"},
        ]
        assert extract_institution_ror_ids(authorships) == ["https://ror.org/abc"]
