"""Behavior-focused unit tests for #10518 (application pipelines, part A).

Covers residual lines in chembl target_helpers / publication_term_transformer,
crossref business-data builder, publication vocab observability, chembl
target protein-classification summary, uniprot gene extractors, and the chembl
target protein-classification transformer.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

from bioetl.application.pipelines.chembl.publication_term_transformer import (
    PublicationTermTransformer,
    _has_extractable_publication_term,
    _prepare_publication_term_record,
    _publication_term_business_data,
    _resolve_publication_term_entity_id,
)
import bioetl.application.pipelines.chembl.publication_term_transformer as ptt_mod
from bioetl.application.pipelines.chembl.target_helpers import (
    ComponentHelper,
    SynonymHelper,
    XrefHelper,
)
from bioetl.application.core.base_transformer import TransformationError
from tests.helpers.transformer_dependencies import build_test_transformer_dependencies


def _make_term_transformer() -> PublicationTermTransformer:
    return PublicationTermTransformer(
        provider="chembl", dependencies=build_test_transformer_dependencies()
    )


# ---------------------------------------------------------------------------
# chembl/target_helpers.py — XrefHelper
# ---------------------------------------------------------------------------


class TestNormalizeXrefSource:
    def test_non_string_returns_none__pipelines_a_1(self) -> None:
        assert XrefHelper.normalize_xref_source(None) is None
        assert XrefHelper.normalize_xref_source(123) is None
        assert XrefHelper.normalize_xref_source(["PDB"]) is None

    def test_blank_returns_none__pipelines_a_1(self) -> None:
        assert XrefHelper.normalize_xref_source("") is None
        assert XrefHelper.normalize_xref_source("   ") is None
        assert XrefHelper.normalize_xref_source("---") is None

    def test_collapses_double_underscores(self) -> None:
        assert XrefHelper.normalize_xref_source("GO--FUNCTION") == "GO_FUNCTION"
        assert XrefHelper.normalize_xref_source("go / function") == "GO_FUNCTION"

    def test_separators_and_case(self) -> None:
        assert XrefHelper.normalize_xref_source(" pdb ") == "PDB"
        assert XrefHelper.normalize_xref_source("go:component") == "GO_COMPONENT"
        assert XrefHelper.normalize_xref_source("go.component") == "GO_COMPONENT"


class TestCleanPipeValue:
    def test_non_string_returns_none__pipelines_a_2(self) -> None:
        assert XrefHelper.clean_pipe_value(None) is None
        assert XrefHelper.clean_pipe_value(42) is None

    def test_blank_returns_none__pipelines_a_2(self) -> None:
        assert XrefHelper.clean_pipe_value("") is None
        assert XrefHelper.clean_pipe_value("  ") is None

    def test_escapes_pipes(self) -> None:
        assert XrefHelper.clean_pipe_value("a|b") == "a\\|b"
        assert XrefHelper.clean_pipe_value("  x  ") == "x"


class TestAppendUniquePipeValue:
    def test_duplicate_is_ignored(self) -> None:
        values = ["a"]
        XrefHelper.append_unique_pipe_value(values, {"a"}, "a")
        assert values == ["a"]

    def test_new_value_appends(self) -> None:
        values: list[str] = []
        seen: set[str] = set()
        XrefHelper.append_unique_pipe_value(values, seen, "a")
        XrefHelper.append_unique_pipe_value(values, seen, "b")
        assert values == ["a", "b"]


class TestCollectComponentXrefs:
    def test_none_and_empty__pipelines_a_1(self) -> None:
        assert XrefHelper.collect_component_xrefs(None) == []
        assert XrefHelper.collect_component_xrefs([]) == []

    def test_drops_non_dict_items(self) -> None:
        components = [
            {
                "target_component_xrefs": [
                    {"xref_src_db": "PDB", "xref_id": "1ABC"},
                    "junk",
                    None,
                ]
            },
            "not-a-dict",
        ]
        assert XrefHelper.collect_component_xrefs(components) == [
            {"xref_src_db": "PDB", "xref_id": "1ABC"}
        ]


class TestProjectComponentXrefs:
    def test_unknown_and_empty_sources_skipped(self) -> None:
        xrefs = [
            {"xref_src_db": "SOMETHING_ELSE", "xref_id": "X1"},
            {"xref_src_db": "", "xref_id": "X2"},
            {"xref_src_db": None, "xref_id": "X3"},
            "not-a-dict",
        ]
        projected = XrefHelper.project_component_xrefs(xrefs)  # type: ignore[list-item]
        assert set(projected) == set(XrefHelper._XREF_DERIVED_COLUMNS)
        assert all(value == "unknown" for value in projected.values())

    def test_missing_value_skipped(self) -> None:
        projected = XrefHelper.project_component_xrefs(
            [{"xref_src_db": "PDB", "xref_id": None}]
        )
        assert projected["target_xref_pdb_ids"] == "unknown"

    def test_projects_and_dedupes(self) -> None:
        xrefs = [
            {"xref_src_db": "PDB", "xref_id": "1ABC"},
            {"xref_src_db": "pdbe", "xref_id": "1ABC"},
            {"xref_src_db": "pdbe", "xref_id": "2DEF"},
            {"xref_src_db": "GO_FUNCTION", "xref_name": "binding"},
            {"xref_src_db": "gofunction", "xref_name": "binding"},
            {"xref_src_db": "HGNC", "xref_id": "5"},
            {"xref_src_db": "UNIPROT", "xref_id": "P12345"},
            {"xref_src_db": "REACTOME", "xref_id": "R1"},
            {"xref_src_db": "GO_COMPONENT", "xref_name": "nucleus"},
            {"xref_src_db": "GO_PROCESS", "xref_name": "growth"},
        ]
        projected = XrefHelper.project_component_xrefs(xrefs)
        assert projected["target_xref_pdb_ids"] == "1ABC|2DEF"
        assert projected["target_xref_go_function"] == "binding"
        assert projected["target_xref_hgnc_ids"] == "5"
        assert projected["target_xref_uniprot_ids"] == "P12345"
        assert projected["target_xref_reactome_ids"] == "R1"
        assert projected["target_xref_go_component"] == "nucleus"
        assert projected["target_xref_go_process"] == "growth"

    def test_pipe_or_unknown(self) -> None:
        assert XrefHelper.pipe_or_unknown([]) == "unknown"
        assert XrefHelper.pipe_or_unknown(["a", "b"]) == "a|b"


# ---------------------------------------------------------------------------
# chembl/target_helpers.py — SynonymHelper
# ---------------------------------------------------------------------------


class TestAppendUniquePipeEscaped:
    def test_none_and_blank_ignored(self) -> None:
        values: list[str] = []
        seen: set[str] = set()
        SynonymHelper.append_unique_pipe_escaped(values, seen, None)
        SynonymHelper.append_unique_pipe_escaped(values, seen, "")
        SynonymHelper.append_unique_pipe_escaped(values, seen, "   ")
        assert values == []

    def test_escapes_and_dedupes(self) -> None:
        values: list[str] = []
        seen: set[str] = set()
        SynonymHelper.append_unique_pipe_escaped(values, seen, "a|b")
        SynonymHelper.append_unique_pipe_escaped(values, seen, "a|b")
        SynonymHelper.append_unique_pipe_escaped(values, seen, 7)
        assert values == ["a\\|b", "7"]


class TestSynonymTargetField:
    def test_non_string_and_blank(self) -> None:
        assert SynonymHelper.synonym_target_field(None) is None
        assert SynonymHelper.synonym_target_field(42) is None
        assert SynonymHelper.synonym_target_field("") is None
        assert SynonymHelper.synonym_target_field("   ") is None

    def test_known_types__pipelines_a_1(self) -> None:
        assert (
            SynonymHelper.synonym_target_field("uniprot") == "target_protein_synonyms"
        )
        assert SynonymHelper.synonym_target_field("EC_NUMBER") == "target_ec_numbers"
        assert (
            SynonymHelper.synonym_target_field("gene_symbol") == "target_gene_synonyms"
        )
        assert (
            SynonymHelper.synonym_target_field("GENE_SYMBOL_HUMAN")
            == "target_gene_synonyms"
        )

    def test_unknown_returns_none__pipelines_a_1(self) -> None:
        assert SynonymHelper.synonym_target_field("OTHER") is None


class TestSynonymProjection:
    def test_iter_skips_invalid_shapes(self) -> None:
        components = [
            "nope",
            {"other": 1},
            {"target_component_synonyms": "nope"},
            {
                "target_component_synonyms": [
                    "nope",
                    {"syn_type": "UNIPROT", "component_synonym": "P1"},
                ]
            },
        ]
        payloads = list(SynonymHelper.iter_component_synonym_payloads(components))  # type: ignore[list-item]
        assert payloads == [{"syn_type": "UNIPROT", "component_synonym": "P1"}]

    def test_project_single_synonym_unknown_field(self) -> None:
        buckets = {
            "target_protein_synonyms": [],
            "target_gene_synonyms": [],
            "target_ec_numbers": [],
        }
        seen: dict[str, set[str]] = {key: set() for key in buckets}
        SynonymHelper.project_single_synonym(
            {"syn_type": "NOPE", "component_synonym": "x"}, buckets, seen
        )
        assert all(not values for values in buckets.values())

    def test_project_single_synonym_applies(self) -> None:
        buckets = {
            "target_protein_synonyms": [],
            "target_gene_synonyms": [],
            "target_ec_numbers": [],
        }
        seen: dict[str, set[str]] = {key: set() for key in buckets}
        SynonymHelper.project_single_synonym(
            {"syn_type": "GENE_SYMBOL", "component_synonym": " TP53 "}, buckets, seen
        )
        assert buckets["target_gene_synonyms"] == ["TP53"]

    def test_empty_projection(self) -> None:
        assert SynonymHelper.empty_synonym_projection() == {
            "target_protein_synonyms": "unknown",
            "target_gene_synonyms": "unknown",
            "target_ec_numbers": "unknown",
        }
        assert SynonymHelper.pipe_or_unknown([]) == "unknown"
        assert SynonymHelper.pipe_or_unknown(["a"]) == "a"

    def test_project_component_synonyms_degenerate(self) -> None:
        assert (
            SynonymHelper.project_component_synonyms(None)
            == SynonymHelper.empty_synonym_projection()
        )
        assert (
            SynonymHelper.project_component_synonyms("nope")
            == SynonymHelper.empty_synonym_projection()
        )  # type: ignore[arg-type]

    def test_project_component_synonyms_full(self) -> None:
        components = [
            {
                "target_component_synonyms": [
                    {"syn_type": "UNIPROT", "component_synonym": "P1"},
                    {"syn_type": "UNIPROT", "component_synonym": "P1"},
                    {"syn_type": "EC_NUMBER", "component_synonym": "1.1.1.1"},
                    {"syn_type": "GENE_SYMBOL_HUMAN", "component_synonym": "TP53"},
                    {"syn_type": "SKIP", "component_synonym": "z"},
                    {"syn_type": "UNIPROT", "component_synonym": None},
                ]
            },
            "junk",
        ]
        assert SynonymHelper.project_component_synonyms(components) == {  # type: ignore[list-item]
            "target_protein_synonyms": "P1",
            "target_gene_synonyms": "TP53",
            "target_ec_numbers": "1.1.1.1",
        }


class TestComponentHelper:
    def test_flatten_degenerate(self) -> None:
        assert (
            ComponentHelper.flatten_target_components(None, MagicMock())
            == ComponentHelper.empty_component_result()
        )
        assert (
            ComponentHelper.flatten_target_components("nope", MagicMock())
            == ComponentHelper.empty_component_result()
        )  # type: ignore[arg-type]

    def test_flatten_delegates_to_basic_fields(self) -> None:
        def fake_extract(components, field, converter):
            assert field in {
                "accession",
                "component_id",
                "component_type",
                "relationship",
                "component_description",
            }
            return [field]

        result = ComponentHelper.flatten_target_components(
            [{"accession": "P1"}], fake_extract
        )
        assert result == {
            "component_accessions": ["accession"],
            "component_ids": ["component_id"],
            "component_types": ["component_type"],
            "component_relationships": ["relationship"],
            "component_descriptions": ["component_description"],
        }

    def test_extract_basic_fields_uses_safe_int(self) -> None:
        from bioetl.domain.transformations import safe_int

        seen: list[tuple[str, object]] = []

        def fake_extract(components, field, converter):
            seen.append((field, converter))
            return None

        ComponentHelper.extract_basic_component_fields(
            [{"accession": "P1"}], fake_extract
        )
        by_field = dict(seen)
        assert by_field["component_id"] is safe_int
        assert by_field["accession"] is None


# ---------------------------------------------------------------------------
# chembl/publication_term_transformer.py
# ---------------------------------------------------------------------------


class TestPublicationTermRecordHelpers:
    def test_prepare_record_legacy_alias(self) -> None:
        record = {"document_chembl_id": "CHEMBL1", "term": "x"}
        prepared = _prepare_publication_term_record(record)
        assert prepared["publication_id"] == "CHEMBL1"
        assert record.get("publication_id") is None

    def test_prepare_record_passthrough(self) -> None:
        record = {"publication_id": "CHEMBL2"}
        assert _prepare_publication_term_record(record) is record
        legacy_none = {"document_chembl_id": None}
        assert _prepare_publication_term_record(legacy_none) is legacy_none

    def test_business_data_drops_entity_id(self) -> None:
        out = _publication_term_business_data({"entity_id": "E", "term": "t"})
        assert out == {"term": "t"}

    def test_resolve_entity_id_matches_compute(self) -> None:
        transformer = _make_term_transformer()
        business = {"publication_id": "CHEMBL1", "term_type": "MESH", "term": "Aspirin"}
        assert _resolve_publication_term_entity_id(
            transformer, business
        ) == transformer.compute_term_entity_id("CHEMBL1", "MESH", "Aspirin")
        assert transformer.compute_term_entity_id(
            "A", "B", "c"
        ) == transformer.compute_term_entity_id("A", "B", "c")

    def test_has_extractable(self) -> None:
        assert _has_extractable_publication_term({"term": "t", "term_type": "y"})
        assert not _has_extractable_publication_term({"term": "", "term_type": "y"})
        assert not _has_extractable_publication_term({"term": "t", "term_type": "  "})
        assert not _has_extractable_publication_term({})


class TestPublicationTermExtractBusinessData:
    def test_direct_branch_full(self) -> None:
        transformer = _make_term_transformer()
        out = transformer._extract_business_data(
            {
                "publication_id": "CHEMBL1",
                "term": "  Aspirin ",
                "term_type": " MESH ",
                "mesh_id": " D1 ",
                "qualifier": " q ",
            },
            "CHEMBL1",
        )
        assert out == {
            "publication_id": "CHEMBL1",
            "term": "Aspirin",
            "term_type": "MESH",
            "mesh_id": "D1",
            "qualifier": "q",
        }

    def test_direct_branch_missing_optional(self) -> None:
        transformer = _make_term_transformer()
        out = transformer._extract_business_data(
            {"publication_id": "CHEMBL1", "term": "t", "term_type": "y"}, "CHEMBL1"
        )
        assert out["mesh_id"] is None
        assert out["qualifier"] is None

    def test_fallback_empty_terms(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            ptt_mod, "extract_terms_from_publication", lambda record, pid: []
        )
        transformer = _make_term_transformer()
        out = transformer._extract_business_data(
            {"publication_id": "CHEMBL1"}, "CHEMBL1"
        )
        assert out == {
            "publication_id": "CHEMBL1",
            "term": "",
            "term_type": "",
            "mesh_id": None,
            "qualifier": None,
        }

    def test_fallback_first_term(self, monkeypatch: pytest.MonkeyPatch) -> None:
        term = {
            "publication_id": "CHEMBL1",
            "term": "t",
            "term_type": "y",
            "mesh_id": None,
            "qualifier": None,
        }
        monkeypatch.setattr(
            ptt_mod,
            "extract_terms_from_publication",
            lambda record, pid: [dict(term, entity_id="E")],
        )
        transformer = _make_term_transformer()
        assert (
            transformer._extract_business_data({"publication_id": "CHEMBL1"}, "CHEMBL1")
            == term
        )

    def test_extract_terms_from_document_maps(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            ptt_mod,
            "extract_terms_from_publication",
            lambda record, pid: [
                {"publication_id": pid, "term": "t", "entity_id": "E"}
            ],
        )
        transformer = _make_term_transformer()
        assert transformer.extract_terms_from_document({"a": 1}, "CHEMBL9") == [
            {"publication_id": "CHEMBL9", "term": "t"}
        ]


class TestPublicationTermPrepareAndStages:
    def test_prepare_returns_none_without_term(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            ptt_mod, "extract_terms_from_publication", lambda record, pid: []
        )
        transformer = _make_term_transformer()
        assert (
            transformer._prepare_term_business_data({"publication_id": "CHEMBL1"})
            is None
        )

    def test_prepare_returns_business_data(self) -> None:
        transformer = _make_term_transformer()
        out = transformer._prepare_term_business_data(
            {"publication_id": "CHEMBL1", "term": "t", "term_type": "y"}
        )
        assert out is not None and out["term"] == "t"

    def test_prepare_missing_primary_id_raises(self) -> None:
        transformer = _make_term_transformer()
        with pytest.raises(TransformationError):
            transformer._prepare_term_business_data({"term": "t", "term_type": "y"})

    async def test_transform_pre_silver_stages(self) -> None:
        transformer = _make_term_transformer()
        staged = await transformer.transform_pre_silver(
            MagicMock(), {"publication_id": "CHEMBL1", "term": "t", "term_type": "y"}, 0
        )
        assert staged is not None
        assert staged.business_data["term"] == "t"

    async def test_transform_pre_silver_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            ptt_mod, "extract_terms_from_publication", lambda record, pid: []
        )
        transformer = _make_term_transformer()
        assert (
            await transformer.transform_pre_silver(
                MagicMock(), {"publication_id": "CHEMBL1"}, 0
            )
            is None
        )

    async def test_transform_impl_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            ptt_mod, "extract_terms_from_publication", lambda record, pid: []
        )
        transformer = _make_term_transformer()
        assert (
            await transformer._transform_impl(
                MagicMock(), {"publication_id": "CHEMBL1"}, 0
            )
            is None
        )


# ---------------------------------------------------------------------------
# crossref/_business_data_builder.py
# ---------------------------------------------------------------------------

from bioetl.application.pipelines.crossref._business_data_builder import (
    _build_crossref_identity_fields,
    _extract_affiliations_input,
    build_crossref_author_block_fields,
    build_crossref_business_data,
    build_crossref_core_block_fields,
    compute_publication_date,
    extract_publication_year_candidate,
    hash_author_details,
)


def _crossref_stubs(**overrides: object) -> dict[str, object]:
    stubs: dict[str, object] = {
        "data_normalizer": SimpleNamespace(
            normalize_author_list=lambda authors: "AUTHORS",
            normalize_author_keys=lambda authors: "KEYS",
            normalize_affiliations=lambda value: "AFFILS",
        ),
        "validate_doi": lambda value: str(value).strip().lower() if value else None,
        "validate_publication_year": lambda value: value,
        "classify_publication_type": lambda value: {
            "publication_type": value,
            "publication_type_raw": value,
        },
        "serialize_json": lambda value: (
            json.dumps(value, sort_keys=True) if value is not None else None
        ),
        "serialize_json_list": lambda value: json.dumps(list(value)) if value else None,
        "hash_pii_value": lambda value: f"HASH:{value}" if value else None,
    }
    stubs.update(overrides)
    return stubs


class TestComputePublicationDate:
    def test_prefers_print(self) -> None:
        assert compute_publication_date("2020-01-01", "2020-02-01") == "2020-01-01"

    def test_falls_back_to_online(self) -> None:
        assert compute_publication_date(None, "2020-02-01") == "2020-02-01"

    def test_both_missing(self) -> None:
        assert compute_publication_date(None, None) is None
        assert compute_publication_date("", "") == ""


class TestHashAuthorDetails:
    def test_hashes_pii_and_preserves_rest(self) -> None:
        authors = [
            {
                "given": "John",
                "family": "Doe",
                "name": "John Doe",
                "orcid": "0000-1",
                "authenticated_orcid": True,
                "sequence": "first",
                "affiliations": [{"name": "Univ"}],
            },
            {"given": "", "family": 5, "name": None},
        ]
        hashed = hash_author_details(authors, hash_pii_value=lambda v: f"H:{v}")
        assert hashed[0]["given"] == "H:John"
        assert hashed[0]["family"] == "H:Doe"
        assert hashed[0]["name"] == "H:John Doe"
        assert hashed[0]["orcid"] == "0000-1"
        assert hashed[0]["affiliations"] == [{"name": "Univ"}]
        assert hashed[1] == {
            "given": None,
            "family": None,
            "name": None,
            "orcid": None,
            "authenticated_orcid": None,
            "sequence": None,
            "affiliations": [],
        }

    def test_empty(self) -> None:
        assert hash_author_details([], hash_pii_value=lambda v: v) == []


class TestExtractPublicationYearCandidate:
    def test_int_year(self) -> None:
        assert (
            extract_publication_year_candidate(
                {"published-print": {"date-parts": [[2021, 5]]}}
            )
            == 2021
        )

    def test_digit_string_year(self) -> None:
        assert (
            extract_publication_year_candidate({"issued": {"date-parts": [["2019"]]}})
            == 2019
        )

    def test_skips_malformed(self) -> None:
        assert extract_publication_year_candidate({}) is None
        assert extract_publication_year_candidate({"published-print": "nope"}) is None
        assert (
            extract_publication_year_candidate(
                {"published-print": {"date-parts": "bad"}}
            )
            is None
        )
        assert (
            extract_publication_year_candidate({"published-print": {"date-parts": []}})
            is None
        )
        assert (
            extract_publication_year_candidate(
                {"published-print": {"date-parts": [[]]}}
            )
            is None
        )
        assert (
            extract_publication_year_candidate(
                {"published-print": {"date-parts": ["2020"]}}
            )
            is None
        )
        assert (
            extract_publication_year_candidate({"issued": {"date-parts": [[None]]}})
            is None
        )


class TestExtractAffiliationsInput:
    def test_prefers_dicts(self) -> None:
        authors = [
            {"affiliations": ["Univ A"]},
            {"affiliations": [{"name": "Univ B"}, 5, None]},
            {"affiliations": "nope"},
            {},
        ]
        assert _extract_affiliations_input(authors) == [{"name": "Univ B"}]

    def test_strings_when_no_dicts(self) -> None:
        assert _extract_affiliations_input([{"affiliations": ["A", "B"]}]) == ["A", "B"]

    def test_none_when_empty(self) -> None:
        assert _extract_affiliations_input([]) is None
        assert _extract_affiliations_input([{}]) is None


class TestCrossrefBuilders:
    def test_identity_fields(self) -> None:
        out = _build_crossref_identity_fields(
            record={"title": ["Hello"], "_lookup_method": "x", "_original_id": "o"},
            doi="10.1/x",
            author_bundle={"authors": "A"},
        )
        assert out["doi"] == "10.1/x"
        assert out["title"] == "Hello"
        assert out["authors"] == "A"
        assert out["_source"] == "crossref"

    def test_core_block(self) -> None:
        stubs = _crossref_stubs()
        out = build_crossref_core_block_fields(
            record={"DOI": "10.1/x", "type": "journal-article"},
            doi="10.1/x",
            classify_publication_type=stubs["classify_publication_type"],  # type: ignore[arg-type]
            serialize_json_list=stubs["serialize_json_list"],  # type: ignore[arg-type]
        )
        assert out["doi"] == "10.1/x"
        assert out["publication_type"] == "journal-article"
        assert out["_dq_warn"] is False

    def test_author_block(self) -> None:
        stubs = _crossref_stubs()
        out = build_crossref_author_block_fields(
            {"author": [{"given": "A", "family": "B"}]},
            data_normalizer=stubs["data_normalizer"],  # type: ignore[arg-type]
            hash_pii_value=stubs["hash_pii_value"],  # type: ignore[arg-type]
            serialize_json=stubs["serialize_json"],  # type: ignore[arg-type]
            serialize_json_list=stubs["serialize_json_list"],  # type: ignore[arg-type]
        )
        assert out["authors"] == "AUTHORS"
        assert out["affiliation_list"] == "AFFILS"

    def test_full_build(self) -> None:
        stubs = _crossref_stubs()
        record = {
            "DOI": "10.1000/XYZ",
            "title": ["Some title"],
            "type": "journal-article",
            "author": [{"given": "A", "family": "B"}],
            "published-print": {"date-parts": [[2021]]},
        }
        out = build_crossref_business_data(record, **stubs)  # type: ignore[arg-type]
        assert out["doi"] == "10.1000/xyz"
        assert out["_source"] == "crossref"
        assert out["publication_year"] == 2021
        assert out["_dq_error"] is False

    def test_full_build_non_string_serialized(self) -> None:
        stubs = _crossref_stubs(
            serialize_json=lambda value: 123, serialize_json_list=lambda value: 456
        )
        record = {"DOI": "10.1/x", "reference": [{"key": "r"}]}
        out = build_crossref_business_data(record, **stubs)  # type: ignore[arg-type]
        assert out["references"] is None
        assert out["references_raw_json"] is None
        assert out["references_canonical_json"] is None

    def test_full_build_rejects_missing_doi(self) -> None:
        stubs = _crossref_stubs()
        with pytest.raises(AssertionError):
            build_crossref_business_data({"title": ["t"]}, **stubs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# common/publication_vocab_observability.py
# ---------------------------------------------------------------------------

from bioetl.application.pipelines.common import (
    publication_vocab_observability as vocab_obs,
)
from bioetl.application.pipelines.common.publication_vocab_observability import (
    _allowed_publication_vocab,
    _field_tokens,
    _normalize_token,
    _normalized_string_tokens,
    _parse_json_sequence,
    _tokens_from_string_value,
    emit_unknown_publication_vocab_metrics,
)


class TestEmitUnknownVocabMetrics:
    def test_noop_without_counter(self) -> None:
        emit_unknown_publication_vocab_metrics(
            metrics=SimpleNamespace(),
            pipeline_name="p",
            provider="crossref",
            normalized_business_data={"publication_type": "weird"},
        )

    def test_unknown_provider_emits_nothing(self) -> None:
        metrics = SimpleNamespace(increment_counter=MagicMock())
        emit_unknown_publication_vocab_metrics(
            metrics=metrics,
            pipeline_name="p",
            provider="nope",
            normalized_business_data={"publication_type": "x"},
        )
        metrics.increment_counter.assert_not_called()

    def test_known_token_emits_nothing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            vocab_obs,
            "_allowed_publication_vocab",
            lambda provider, field: frozenset({"known"}),
        )
        metrics = SimpleNamespace(increment_counter=MagicMock())
        emit_unknown_publication_vocab_metrics(
            metrics=metrics,
            pipeline_name="p",
            provider="crossref",
            normalized_business_data={"publication_type": "known"},
        )
        metrics.increment_counter.assert_not_called()

    def test_unknown_token_increments(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            vocab_obs,
            "_allowed_publication_vocab",
            lambda provider, field: frozenset({"known"}),
        )
        metrics = SimpleNamespace(increment_counter=MagicMock())
        emit_unknown_publication_vocab_metrics(
            metrics=metrics,
            pipeline_name="pipe",
            provider="crossref",
            normalized_business_data={"publication_type": "weird-type"},
        )
        metrics.increment_counter.assert_called_once()
        kwargs = metrics.increment_counter.call_args.kwargs
        assert kwargs["name"] == vocab_obs.PUBLICATION_RAW_VOCAB_UNKNOWN_TOTAL
        assert kwargs["value"] == 1
        assert kwargs["labels"] == {
            "pipeline": "pipe",
            "provider": "crossref",
            "field": "publication_type",
            "handling": "preserved_unknown",
        }

    def test_empty_allowed_skips_field(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            vocab_obs, "_allowed_publication_vocab", lambda provider, field: frozenset()
        )
        metrics = SimpleNamespace(increment_counter=MagicMock())
        emit_unknown_publication_vocab_metrics(
            metrics=metrics,
            pipeline_name="p",
            provider="crossref",
            normalized_business_data={"publication_type": "x"},
        )
        metrics.increment_counter.assert_not_called()


class TestVocabTokenHelpers:
    def test_field_tokens_shapes(self) -> None:
        assert _field_tokens(" Journal Article ") == ("Journal Article",)
        assert _field_tokens([" a ", "", None, 5]) == ("a",)
        assert _field_tokens(42) == ()
        assert _field_tokens(None) == ()

    def test_tokens_from_string_json_list(self) -> None:
        assert _tokens_from_string_value('["a", " b "]') == ("a", "b")

    def test_tokens_from_string_plain_and_blank(self) -> None:
        assert _tokens_from_string_value("  ") == ()
        assert _tokens_from_string_value("hello") == ("hello",)

    def test_parse_json_sequence(self) -> None:
        assert _parse_json_sequence('["a"]') == ["a"]
        assert _parse_json_sequence("not-json{{{") is None
        assert _parse_json_sequence('"just-a-string"') is None
        assert _parse_json_sequence("5") is None

    def test_normalize_token_passthrough(self) -> None:
        assert _normalize_token(" x ") == "x"
        assert _normalize_token("  ") is None

    def test_normalized_string_tokens_filters(self) -> None:
        assert _normalized_string_tokens([" a ", None, "  ", 3]) == ("a",)

    def test_allowed_vocab_real_fn(self) -> None:
        assert isinstance(
            _allowed_publication_vocab("crossref", "publication_type"), frozenset
        )


# ---------------------------------------------------------------------------
# chembl/target_protein_classification_summary.py
# ---------------------------------------------------------------------------

import polars as pl

import bioetl.application.pipelines.chembl.target_protein_classification_summary as summ
from bioetl.application.pipelines.chembl.target_protein_classification_summary import (
    _classification_sort_key,
    _deduplicate_resolved_rows,
    _int_or_none,
    _is_resolved,
    _positive_int_or_none,
    _text_or_none,
    empty_target_protein_classification_summary,
    summarize_target_protein_classification_dependency,
    summarize_target_protein_classification_rows,
)


def _summary_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "target_id": "T1",
        "classification_status": "resolved",
        "component_id": 1,
        "leaf_id": 10,
        "l1_id": 1,
        "l1_name": "Kinase",
        "l1_desc": "desc",
    }
    row.update(overrides)
    return row


def _patch_summary_derivation(
    monkeypatch: pytest.MonkeyPatch, *, multifunctional: bool = False
) -> None:
    def fake_derive(rows: object, mapping_data: object) -> SimpleNamespace:
        items = list(rows)  # type: ignore[arg-type]
        kind = "multifunctional" if multifunctional else "single"
        if len(items) > 1:
            return SimpleNamespace(
                target_protein_class_type=kind,
                top_level_count=2,
                canonical_top_levels=("TOP",),
                counted_top_levels=("TOP",),
                ignored_top_levels=(),
                primary_top_level="TOP",
                reason_code="r",
                rule_version="rv",
                mapping_version="mv",
            )
        return SimpleNamespace(
            target_protein_class_type="single",
            top_level_count=1,
            canonical_top_levels=("OTHER",),
            counted_top_levels=("OTHER",),
            ignored_top_levels=(),
            primary_top_level="OTHER",
            reason_code="r",
            rule_version="rv",
            mapping_version="mv",
        )

    monkeypatch.setattr(summ, "derive_protein_class_target_type", fake_derive)
    monkeypatch.setattr(summ, "derive_major_families", lambda rows: ("FAM",))
    monkeypatch.setattr(
        summ, "current_protein_class_target_type_mapping", lambda: object()
    )


class TestSummarizeDependency:
    def test_missing_target_id_column_returns_input(self) -> None:
        df = pl.DataFrame({"other": ["x"]})
        assert summarize_target_protein_classification_dependency(df).equals(df)

    def test_empty_frame_returns_schema(self) -> None:
        df = pl.DataFrame(schema={"target_id": pl.Utf8})
        result = summarize_target_protein_classification_dependency(df)
        assert result.is_empty()
        assert "target_id" in result.columns

    def test_skips_blank_targets(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_summary_derivation(monkeypatch)
        df = pl.DataFrame(
            [
                {"target_id": None, "component_id": 1, "leaf_id": 5},
                {"target_id": "  ", "component_id": 1, "leaf_id": 6},
                {"target_id": "T1", "component_id": 1, "leaf_id": 7},
            ]
        )
        result = summarize_target_protein_classification_dependency(df)
        assert result["target_id"].to_list() == ["T1"]

    def test_representative_falls_back_to_first_row(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Multi-row derive reports primary TOP, but no single row counts as TOP.
        _patch_summary_derivation(monkeypatch)
        summary = summarize_target_protein_classification_rows(
            "T1", [_summary_row(leaf_id=10), _summary_row(leaf_id=11)]
        )
        assert summary["target_id"] == "T1"
        assert summary["target_protein_class_name_L1"] == "Kinase"

    def test_multifunctional_origin_multi_component(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_summary_derivation(monkeypatch, multifunctional=True)
        summary = summarize_target_protein_classification_rows(
            "T1",
            [
                _summary_row(component_id=1, leaf_id=10),
                _summary_row(component_id=2, leaf_id=11),
            ],
        )
        assert summary["multifunctional_origin"] == "multi_component_heterogeneity"

    def test_multifunctional_origin_single_component(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_summary_derivation(monkeypatch, multifunctional=True)
        summary = summarize_target_protein_classification_rows(
            "T1",
            [
                _summary_row(component_id=1, leaf_id=10),
                _summary_row(component_id=1, leaf_id=11),
            ],
        )
        assert summary["multifunctional_origin"] == "multiple_informative_top_levels"

    def test_no_resolved_rows_returns_base_summary(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_summary_derivation(monkeypatch)
        summary = summarize_target_protein_classification_rows(
            "T1", [_summary_row(classification_status="quarantined", leaf_id=10)]
        )
        assert summary["target_id"] == "T1"
        assert summary["protein_classifications"] is None

    def test_missing_primary_marks_multifunctional(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def fake_derive(rows: object, mapping_data: object) -> SimpleNamespace:
            return SimpleNamespace(
                target_protein_class_type="multifunctional",
                top_level_count=2,
                canonical_top_levels=("A", "B"),
                counted_top_levels=("A", "B"),
                ignored_top_levels=(),
                primary_top_level=None,
                reason_code="r",
                rule_version="rv",
                mapping_version="mv",
            )

        monkeypatch.setattr(summ, "derive_protein_class_target_type", fake_derive)
        monkeypatch.setattr(summ, "derive_major_families", lambda rows: ("FAM",))
        monkeypatch.setattr(
            summ, "current_protein_class_target_type_mapping", lambda: object()
        )
        summary = summarize_target_protein_classification_rows(
            "T1", [_summary_row(leaf_id=10), _summary_row(leaf_id=11)]
        )
        assert (
            summary["target_protein_class_name_L1"] == summ.MULTIFUNCTIONAL_TARGET_NAME
        )
        assert (
            summary["target_protein_class_name_L2"] == summ.MULTIFUNCTIONAL_TARGET_NAME
        )
        assert summary["target_protein_class_name_L3"] == ""

    def test_empty_summary_defaults(self) -> None:
        row = empty_target_protein_classification_summary("T9")
        assert row["target_id"] == "T9"
        assert row["target_protein_class_type"] == "unknown"
        assert row["top_level_count"] == 0


class TestSummaryRowHelpers:
    def test_dedupe_skips_unresolved_and_bad_leaf(self) -> None:
        rows = [
            _summary_row(leaf_id=10),
            _summary_row(leaf_id=10, component_id=2),
            _summary_row(leaf_id=11, classification_status="quarantined"),
            _summary_row(leaf_id=None),
        ]
        assert [row["leaf_id"] for row in _deduplicate_resolved_rows(rows)] == [10]

    def test_is_resolved(self) -> None:
        assert _is_resolved({"classification_status": None})
        assert _is_resolved({})
        assert _is_resolved({"classification_status": "resolved"})
        assert not _is_resolved({"classification_status": "quarantined"})

    def test_sort_key_orders_unresolved_last(self) -> None:
        first = _classification_sort_key(_summary_row(leaf_id=1))
        last = _classification_sort_key(
            _summary_row(leaf_id=1, classification_status="quarantined")
        )
        assert first < last

    def test_text_or_none(self) -> None:
        assert _text_or_none(None) is None
        assert _text_or_none("  ") is None
        assert _text_or_none(" x ") == "x"

    def test_positive_int_or_none(self) -> None:
        assert _positive_int_or_none(0) is None
        assert _positive_int_or_none(-3) is None
        assert _positive_int_or_none(4) == 4
        assert _positive_int_or_none("7") == 7

    def test_int_or_none_branches(self) -> None:
        assert _int_or_none(None) is None
        assert _int_or_none(True) is None
        assert _int_or_none(False) is None
        assert _int_or_none(5) == 5
        assert _int_or_none(2.5) is None
        assert _int_or_none(3.0) == 3
        assert _int_or_none("  ") is None
        assert _int_or_none("42") == 42
        assert _int_or_none("abc") is None
        assert _int_or_none(object()) is None


# ---------------------------------------------------------------------------
# uniprot/extractors/genes.py
# ---------------------------------------------------------------------------

from bioetl.application.pipelines.uniprot.extractors.genes import GeneExtractor


class TestGeneExtractor:
    def test_iter_gene_dicts_filters(self) -> None:
        assert GeneExtractor._iter_gene_dicts(None) == []
        assert GeneExtractor._iter_gene_dicts("nope") == []
        assert GeneExtractor._iter_gene_dicts([{"a": 1}, "x", None]) == [{"a": 1}]

    def test_collect_named_values_shapes(self) -> None:
        genes = [
            {"synonyms": [{"value": "S1"}, {"nope": 1}, "junk", {"value": ""}]},
            {"synonyms": "nope"},
            {"other": 1},
            "junk",
        ]
        assert GeneExtractor._collect_named_values(genes, "synonyms") == ["S1"]
        assert GeneExtractor._collect_named_values(None, "synonyms") == []

    def test_extract_gene_names(self) -> None:
        genes = [
            {"geneName": {"value": "BRCA1"}},
            {"geneName": {"value": ""}},
            {"geneName": "nope"},
            {"other": 1},
        ]
        assert GeneExtractor.extract_gene_names(genes) == ["BRCA1"]
        assert GeneExtractor.extract_gene_names(None) == []

    def test_extract_primary_gene(self) -> None:
        assert (
            GeneExtractor.extract_primary_gene([{"geneName": {"value": "TP53"}}])
            == "TP53"
        )
        assert (
            GeneExtractor.extract_primary_gene([{"geneName": "nope"}, {"geneName": {}}])
            is None
        )
        assert GeneExtractor.extract_primary_gene(None) is None
        assert GeneExtractor.extract_primary_gene([{"geneName": {"value": ""}}]) is None

    def test_extract_synonyms_and_orf(self) -> None:
        genes = [{"synonyms": [{"value": "S1"}], "orfNames": [{"value": "O1"}]}]
        assert json.loads(GeneExtractor.extract_gene_synonyms(genes)) == ["S1"]  # type: ignore[arg-type]
        assert json.loads(GeneExtractor.extract_gene_orf_names(genes)) == ["O1"]  # type: ignore[arg-type]
        assert GeneExtractor.extract_gene_synonyms([]) is None
        assert GeneExtractor.extract_gene_orf_names(None) is None


# ---------------------------------------------------------------------------
# chembl/target_protein_classification_transformer.py
# ---------------------------------------------------------------------------

from bioetl.application.pipelines.chembl.target_protein_classification_transformer import (
    TargetProteinClassificationTransformer,
    _classification_status,
    _optional_bool,
    _optional_id_text,
    _optional_int,
    _optional_text,
    _target_classification_entity_id,
)
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunType
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite


def _make_classification_transformer() -> TargetProteinClassificationTransformer:
    return TargetProteinClassificationTransformer(
        provider="chembl", dependencies=build_test_transformer_dependencies()
    )


class TestTargetClassificationTransformer:
    async def test_transform_pre_silver(self) -> None:
        transformer = _make_classification_transformer()
        staged = await transformer.transform_pre_silver(
            MagicMock(), {"target_id": "T1"}, 0
        )
        assert staged is not None
        assert staged.entity_id == "T1:missing_classification"
        assert staged.business_data["target_id"] == "T1"

    def test_extract_business_data_defaults(self) -> None:
        transformer = _make_classification_transformer()
        out = transformer._extract_business_data(
            {"target_id": "T1", "component_id": "3"}, "T1"
        )
        assert out["component_id"] == 3
        assert out["classification_status"] == "missing_classification"
        assert out["leaf_id"] is None

    async def test_transform_impl_resolved(self) -> None:
        transformer = _make_classification_transformer()
        logger = MagicMock()
        logger.bind = MagicMock(return_value=logger)
        context = PipelineContext(
            run_id=deterministic_uuid_from_callsite("issue_10518_classification_impl"),
            run_type=RunType.INCREMENTAL,
            logger=logger,
        )
        record = {
            "target_id": "CHEMBL123",
            "classification_status": "resolved",
            "component_id": "10",
            "leaf_id": "148",
        }
        silver = await transformer._transform_impl(context, record, 0)  # type: ignore[arg-type]
        assert silver is not None
        assert silver["target_id"] == "CHEMBL123"

    def test_entity_id_resolved(self) -> None:
        assert (
            _target_classification_entity_id(
                {
                    "target_id": "T",
                    "classification_status": "resolved",
                    "component_id": 1,
                    "leaf_id": 2,
                }
            )
            == "T:1:2"
        )

    def test_entity_id_resolved_requires_ids(self) -> None:
        with pytest.raises(ValueError):
            _target_classification_entity_id(
                {
                    "target_id": "T",
                    "classification_status": "resolved",
                    "component_id": None,
                    "leaf_id": 2,
                }
            )
        with pytest.raises(ValueError):
            _target_classification_entity_id(
                {"target_id": "T", "classification_status": "resolved"}
            )

    def test_entity_id_non_resolved(self) -> None:
        assert (
            _target_classification_entity_id(
                {"target_id": "T", "classification_status": "quarantined"}
            )
            == "T:quarantined"
        )

    def test_classification_status(self) -> None:
        assert _classification_status(None) == "missing_classification"
        assert _classification_status("resolved") == "resolved"
        assert _classification_status("  quarantined  ") == "quarantined"
        with pytest.raises(ValueError):
            _classification_status("bogus")

    def test_optional_helpers(self) -> None:
        assert _optional_int("5") == 5
        assert _optional_text(" x ") == "x"
        assert _optional_id_text(12) == "12"
        assert _optional_id_text(None) is None
        assert _optional_bool(None) is None
        assert _optional_bool(True) is True
        assert _optional_bool(0) is False
        assert _optional_bool(2) is True
        assert _optional_bool("yes") is True
        assert _optional_bool("No") is False
        assert _optional_bool("maybe") is None
        assert _optional_bool(3.5) is None
