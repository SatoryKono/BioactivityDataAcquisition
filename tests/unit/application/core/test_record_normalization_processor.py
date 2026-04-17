"""Unit tests for application-owned record normalization stage."""

from __future__ import annotations

import json

import pytest
from hypothesis import given
from hypothesis import strategies as st

from bioetl.application.core.config import (
    ContentHashPolicyByVersion,
    ContentHashVersionPolicy,
)
from bioetl.application.core.pre_silver_record import PreSilverRecord
from bioetl.application.core.record_normalization_processor import (
    NormalizationContractError,
    RecordNormalizationProcessor,
)
from bioetl.domain.transformations import generate_content_hash


@pytest.mark.unit
def test_normalize_record_applies_identifier_date_json_and_hash_rules() -> None:
    processor = RecordNormalizationProcessor(provider="crossref")
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


@pytest.mark.unit
def test_compute_content_hash_is_idempotent_for_normalized_payload() -> None:
    processor = RecordNormalizationProcessor(provider="crossref")
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
    processor = RecordNormalizationProcessor(provider="crossref")

    normalized = processor.normalize_record(
        {"entity_id": "crossref:1", "content_hash": "stale", "raw_json": "{not json}"}
    )

    assert normalized["raw_json"] == "{not json}"


@pytest.mark.unit
def test_compute_content_hashes_by_version_returns_ordered_multi_hash_payload() -> None:
    processor = RecordNormalizationProcessor(
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
def test_finalize_pre_silver_attaches_active_and_versioned_content_hashes() -> None:
    processor = RecordNormalizationProcessor(
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
        context=object(),
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
    processor = RecordNormalizationProcessor(
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
        context=object(),
        index=0,
    )

    assert silver_record is not None
    assert "_content_hashes_by_version" not in silver_record


@pytest.mark.unit
def test_profile_auto_resolves_for_chembl_activity() -> None:
    processor = RecordNormalizationProcessor(
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
    processor = RecordNormalizationProcessor(
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
    processor = RecordNormalizationProcessor(
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
def test_processor_without_profile_keeps_legacy_fallback_behavior() -> None:
    processor = RecordNormalizationProcessor(
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
    processor = RecordNormalizationProcessor(
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
    processor = RecordNormalizationProcessor(
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
def test_profile_auto_resolves_for_semanticscholar_publication() -> None:
    processor = RecordNormalizationProcessor(
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
    processor = RecordNormalizationProcessor(
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
        }
    )

    assert processor.profile is not None
    assert normalized["component_id"] == 42
    assert normalized["taxonomy_id"] == 9606
    assert normalized["protein_classification_id"] == 7
    assert normalized["target_component_synonyms"] == '[{"name":"B"},{"name":"A"}]'
    assert normalized["protein_classification_ids"] == "[7,3,5]"


@pytest.mark.unit
def test_profile_auto_resolves_for_chembl_publication_similarity() -> None:
    processor = RecordNormalizationProcessor(
        provider="chembl",
        entity_type="publication_similarity",
    )

    normalized = processor.normalize_business_data(
        {
            "sim_id": " 4 ",
            "doc_1": " 10 ",
            "doc_2": " 11 ",
            "pubmed_id1": " PMID:12345 ",
            "pubmed_id2": " 67890 ",
            "avg_tani": " 0.7500000000 ",
        }
    )

    assert processor.profile is not None
    assert normalized["sim_id"] == 4
    assert normalized["doc_1"] == 10
    assert normalized["doc_2"] == 11
    assert normalized["pubmed_id1"] == "12345"
    assert normalized["pubmed_id2"] == "67890"
    assert normalized["avg_tani"] == pytest.approx(0.75)


@pytest.mark.unit
def test_openalex_publication_profile_makes_content_hash_invariant_for_set_like_lists() -> (
    None
):
    processor = RecordNormalizationProcessor(
        provider="openalex",
        entity_type="publication",
    )
    record_a = {
        "entity_id": "openalex:1",
        "content_hash": "stale-a",
        "openalex_id": "W1",
        "doi": "HTTPS://doi.org/10.1000/ABC",
        "title": " Example title ",
        "publication_date": "2024-02",
        "institution_ids": ["i2", "i1"],
        "subject_keywords": ["z", "a"],
        "_source": "legacy-openalex-a",
        "_run_id": "run-a",
    }
    record_b = {
        "entity_id": "openalex:2",
        "content_hash": "stale-b",
        "openalex_id": "W1",
        "doi": "10.1000/abc",
        "title": "Example title",
        "publication_date": "2024-02-29",
        "institution_ids": ["i1", "i2"],
        "subject_keywords": ["a", "z"],
        "_source": "legacy-openalex-b",
        "_run_id": "run-b",
    }
    changed_record = {
        "entity_id": "openalex:3",
        "content_hash": "stale-c",
        "openalex_id": "W1",
        "doi": "10.1000/abc",
        "title": "Example title",
        "publication_date": "2024-02-29",
        "institution_ids": ["i1", "i2"],
        "subject_keywords": ["a", "changed"],
        "_source": "legacy-openalex-c",
        "_run_id": "run-c",
    }

    normalized_a = processor.normalize_record(record_a)
    normalized_b = processor.normalize_record(record_b)
    normalized_changed = processor.normalize_record(changed_record)

    assert normalized_a["content_hash"] == normalized_b["content_hash"]
    assert normalized_changed["content_hash"] != normalized_a["content_hash"]


@pytest.mark.unit
def test_uniprot_protein_profile_makes_content_hash_invariant_for_gene_name_order() -> (
    None
):
    processor = RecordNormalizationProcessor(
        provider="uniprot",
        entity_type="protein",
    )
    record_a = {
        "entity_id": "uniprot:1",
        "content_hash": "stale-a",
        "accession": "P12345",
        "protein_name": " Example <b>protein</b> ",
        "annotation_score": "5",
        "gene_names": ["GENE2", "GENE1"],
        "organism_id": "9606",
        "_run_id": "run-a",
    }
    record_b = {
        "entity_id": "uniprot:2",
        "content_hash": "stale-b",
        "accession": "P12345",
        "protein_name": "Example protein",
        "annotation_score": 5,
        "gene_names": ["GENE1", "GENE2"],
        "organism_id": 9606.0,
        "_run_id": "run-b",
    }
    changed_record = {
        "entity_id": "uniprot:3",
        "content_hash": "stale-c",
        "accession": "P12345",
        "protein_name": "Example protein",
        "annotation_score": 5,
        "gene_names": ["GENE1", "GENE3"],
        "organism_id": 9606,
        "_run_id": "run-c",
    }

    normalized_a = processor.normalize_record(record_a)
    normalized_b = processor.normalize_record(record_b)
    normalized_changed = processor.normalize_record(changed_record)

    assert normalized_a["protein_name"] == "Example protein"
    assert normalized_a["organism_id"] == 9606
    assert normalized_a["content_hash"] == normalized_b["content_hash"]
    assert normalized_changed["content_hash"] != normalized_a["content_hash"]


@pytest.mark.unit
def test_chembl_activity_profile_makes_content_hash_invariant_for_set_like_json_arrays() -> (
    None
):
    processor = RecordNormalizationProcessor(
        provider="chembl",
        entity_type="activity",
    )
    record_a = {
        "entity_id": "chembl:1",
        "content_hash": "stale-a",
        "activity_id": "CHEMBL25",
        "publication_doi": "10.1000/abc",
        "activity_properties": '[{"kind":"a","rank":1},{"kind":"b","rank":2}]',
        "_run_id": "run-a",
    }
    record_b = {
        "entity_id": "chembl:1",
        "content_hash": "stale-b",
        "activity_id": "CHEMBL25",
        "publication_doi": "10.1000/abc",
        "activity_properties": '[{"kind":"b","rank":2},{"kind":"a","rank":1}]',
        "_run_id": "run-b",
    }

    normalized_a = processor.normalize_record(record_a)
    normalized_b = processor.normalize_record(record_b)

    assert normalized_a["content_hash"] == normalized_b["content_hash"]


@pytest.mark.unit
def test_chembl_activity_content_hash_matches_golden_value() -> None:
    processor = RecordNormalizationProcessor(
        provider="chembl",
        entity_type="activity",
    )

    normalized = processor.normalize_record(
        {
            "entity_id": "chembl:1",
            "content_hash": "stale",
            "activity_id": " CHEMBL25 ",
            "publication_doi": " HTTPS://doi.org/10.1000/ABC ",
            "publication_pmid": " 12345 ",
            "standard_value": "1.2300000000",
            "activity_properties": (' [{"kind":"b","rank":2},{"rank":1,"kind":"a"}] '),
            "_run_id": "run-1",
        }
    )

    assert (
        normalized["content_hash"]
        == "c066788d40b9881e1872940148940e127e498ca83dad4cecc88bab05abf34972"
    )


@pytest.mark.unit
def test_chembl_activity_content_hash_ignores_meta_fields_and_equivalent_scalars() -> (
    None
):
    processor = RecordNormalizationProcessor(
        provider="chembl",
        entity_type="activity",
    )
    record_a = {
        "entity_id": "chembl:1",
        "content_hash": "stale-a",
        "activity_id": "CHEMBL25",
        "publication_doi": "https://doi.org/10.1000/ABC",
        "publication_pmid": "0012345",
        "standard_value": "1.2300000000",
        "activity_properties": '[{"kind":"a","rank":1},{"kind":"b","rank":2}]',
        "_run_id": "run-a",
        "_source_batch_id": "batch-a",
        "_index": 1,
    }
    record_b = {
        "entity_id": "chembl:2",
        "content_hash": "stale-b",
        "activity_id": "CHEMBL25",
        "publication_doi": "10.1000/abc",
        "publication_pmid": 12345,
        "standard_value": 1.23,
        "activity_properties": '[{"kind":"b","rank":2},{"kind":"a","rank":1}]',
        "_run_id": "run-b",
        "_source_batch_id": "batch-b",
        "_index": 999,
    }

    normalized_a = processor.normalize_record(record_a)
    normalized_b = processor.normalize_record(record_b)

    assert normalized_a["content_hash"] == normalized_b["content_hash"]
    assert normalized_a["publication_pmid"] == "12345"
    assert normalized_b["publication_pmid"] == "12345"


@pytest.mark.unit
def test_chembl_activity_content_hash_is_stable_for_equivalent_identifier_and_json_forms() -> (
    None
):
    processor = RecordNormalizationProcessor(
        provider="chembl",
        entity_type="activity",
    )
    record_a = {
        "entity_id": "chembl:1",
        "content_hash": "stale-a",
        "activity_id": "CHEMBL25",
        "publication_doi": " HTTPS://doi.org/10.1000/ABC ",
        "publication_pmid": "0012345",
        "standard_value": "1.2300000000",
        "activity_properties": '[{"kind":"a","rank":1},{"kind":"b","rank":2}]',
    }
    record_b = {
        "entity_id": "chembl:9",
        "content_hash": "stale-b",
        "activity_id": "CHEMBL25",
        "publication_doi": "10.1000/abc",
        "publication_pmid": 12345,
        "standard_value": 1.23,
        "activity_properties": '[{"rank":2,"kind":"b"},{"rank":1,"kind":"a"}]',
    }

    normalized_a = processor.normalize_record(record_a)
    normalized_b = processor.normalize_record(record_b)

    assert normalized_a["publication_doi"] == "10.1000/abc"
    assert normalized_b["publication_pmid"] == "12345"
    assert normalized_a["activity_properties"] != normalized_b["activity_properties"]
    assert normalized_a["content_hash"] == normalized_b["content_hash"]


@pytest.mark.unit
def test_chembl_activity_content_hash_treats_blank_identifier_fields_like_none() -> (
    None
):
    processor = RecordNormalizationProcessor(
        provider="chembl",
        entity_type="activity",
    )
    record_a = {
        "entity_id": "chembl:1",
        "content_hash": "stale-a",
        "activity_id": "CHEMBL25",
        "publication_doi": "   ",
        "publication_pmid": None,
        "standard_value": "1.23",
    }
    record_b = {
        "entity_id": "chembl:1",
        "content_hash": "stale-b",
        "activity_id": "CHEMBL25",
        "publication_doi": None,
        "publication_pmid": "",
        "standard_value": 1.23,
    }

    normalized_a = processor.normalize_record(record_a)
    normalized_b = processor.normalize_record(record_b)

    assert normalized_a["publication_doi"] is None
    assert normalized_b["publication_pmid"] is None
    assert normalized_a["content_hash"] == normalized_b["content_hash"]


@pytest.mark.unit
def test_normalize_record_softly_drops_invalid_smiles_from_payload_and_hash() -> None:
    processor = RecordNormalizationProcessor(provider="pubchem")
    record_with_invalid_smiles = {
        "entity_id": "pubchem:1",
        "content_hash": "stale-a",
        "molecule_id": "2244",
        "canonical_smiles": "invalid smiles with spaces",
        "isomeric_smiles": "  C[C@H](O)CC  ",
    }
    record_with_missing_smiles = {
        "entity_id": "pubchem:1",
        "content_hash": "stale-b",
        "molecule_id": "2244",
        "canonical_smiles": None,
        "isomeric_smiles": "C[C@H](O)CC",
    }

    normalized_invalid = processor.normalize_record(record_with_invalid_smiles)
    normalized_missing = processor.normalize_record(record_with_missing_smiles)

    assert normalized_invalid["canonical_smiles"] is None
    assert normalized_invalid["isomeric_smiles"] == "C[C@H](O)CC"
    assert normalized_invalid["content_hash"] == normalized_missing["content_hash"]


@pytest.mark.unit
def test_chembl_activity_profile_normalizes_canonical_smiles_via_smiles_value_object() -> (
    None
):
    processor = RecordNormalizationProcessor(
        provider="chembl",
        entity_type="activity",
    )

    normalized = processor.normalize_business_data(
        {
            "activity_id": "CHEMBL25",
            "canonical_smiles": " invalid smiles with spaces ",
            "standard_value": "1.23",
        }
    )

    assert normalized["canonical_smiles"] is None


@pytest.mark.unit
@given(
    activity_properties=st.permutations(
        (
            {"kind": "a", "rank": 1},
            {"kind": "b", "rank": 2},
            {"kind": "c", "rank": 3},
        )
    )
)
def test_chembl_activity_content_hash_is_permutation_invariant_for_set_like_json(
    activity_properties: tuple[dict[str, object], ...],
) -> None:
    processor = RecordNormalizationProcessor(
        provider="chembl",
        entity_type="activity",
    )
    base_record = {
        "entity_id": "chembl:1",
        "content_hash": "stale",
        "activity_id": "CHEMBL25",
        "publication_doi": "10.1000/abc",
        "standard_value": 1.23,
        "_run_id": "run-1",
    }
    canonical = processor.normalize_record(
        {
            **base_record,
            "activity_properties": (
                '[{"kind":"a","rank":1},{"kind":"b","rank":2},{"kind":"c","rank":3}]'
            ),
        }
    )
    candidate = processor.normalize_record(
        {
            **base_record,
            "activity_properties": json.dumps(list(activity_properties)),
        }
    )

    assert canonical["content_hash"] == candidate["content_hash"]


@pytest.mark.unit
def test_crossref_publication_profile_stabilizes_identifier_date_and_set_like_content_hash() -> (
    None
):
    processor = RecordNormalizationProcessor(
        provider="crossref", entity_type="publication"
    )

    normalized = processor.normalize_business_data(
        {
            "doi": " https://doi.org/10.1000/XYZ ",
            "publication_date": " 2024-01-02 ",
            "title": "  Example   Title ",
            "issue": " 12 ",
            "volume": " 34 ",
            "_source": "legacy-crossref",
        }
    )

    assert normalized["doi"] == "10.1000/xyz"
    assert normalized["publication_date"] == "2024-01-02"
    assert normalized["title"] == "Example Title"
    assert normalized["issue"] == "12"
    assert normalized["volume"] == "34"
    assert normalized["_source"] == "legacy-crossref"
    assert processor.compute_content_hash({"subject_keywords": ["alpha", "beta"]}) == (
        processor.compute_content_hash({"subject_keywords": ["beta", "alpha"]})
    )
    assert processor.compute_content_hash({"subject_keywords": ["alpha", "beta"]}) != (
        processor.compute_content_hash({"subject_keywords": ["alpha", "gamma"]})
    )


@pytest.mark.unit
def test_chembl_assay_profile_makes_content_hash_invariant_for_equivalent_scalar_and_json_forms() -> (
    None
):
    processor = RecordNormalizationProcessor(provider="chembl", entity_type="assay")
    record_a = {
        "entity_id": "chembl:assay-a",
        "content_hash": "stale-a",
        "assay_id": " CHEMBL-ASSAY-1 ",
        "target_id": " CHEMBL-TARGET-1 ",
        "assay_pref_name": " Example <b>Assay</b> ",
        "confidence_score": "7",
        "assay_taxonomy_id": "9606",
        "score": "1.2300000000",
        "variant_sequence_json": '{"b":2,"a":1}',
        "_run_id": "run-a",
        "_source_batch_id": "batch-a",
    }
    record_b = {
        "entity_id": "chembl:assay-b",
        "content_hash": "stale-b",
        "assay_id": "CHEMBL-ASSAY-1",
        "target_id": "CHEMBL-TARGET-1",
        "assay_pref_name": "Example Assay",
        "confidence_score": 7,
        "assay_taxonomy_id": 9606.0,
        "score": 1.23,
        "variant_sequence_json": '{"a":1,"b":2}',
        "_run_id": "run-b",
        "_source_batch_id": "batch-b",
    }

    normalized_a = processor.normalize_record(record_a)
    normalized_b = processor.normalize_record(record_b)

    assert normalized_a["assay_pref_name"] == "Example Assay"
    assert normalized_a["confidence_score"] == 7
    assert normalized_a["assay_taxonomy_id"] == pytest.approx(9606.0)
    assert normalized_a["variant_sequence_json"] == '{"a":1,"b":2}'
    assert normalized_a["content_hash"] == normalized_b["content_hash"]


@pytest.mark.unit
def test_chembl_publication_profile_makes_content_hash_invariant_for_equivalent_identifier_and_date_forms() -> (
    None
):
    processor = RecordNormalizationProcessor(
        provider="chembl", entity_type="publication"
    )
    record_a = {
        "entity_id": "chembl:publication-a",
        "content_hash": "stale-a",
        "publication_id": "CHEMBL-PUB-1",
        "title": " Example <b>Publication</b> ",
        "doi": " HTTPS://doi.org/10.1000/ABC ",
        "publication_doi": "10.1000/ABC",
        "pmid": " PMID:12345 ",
        "publication_pmc_id": " pmc123 ",
        "publication_date": "2024-02",
        "citations_received": "12",
        "_source": "legacy-source-a",
        "_run_id": "run-a",
        "_source_batch_id": "batch-a",
        "_original_id": "legacy-a",
    }
    record_b = {
        "entity_id": "chembl:publication-b",
        "content_hash": "stale-b",
        "publication_id": "CHEMBL-PUB-1",
        "title": "Example Publication",
        "doi": "10.1000/abc",
        "publication_doi": "https://doi.org/10.1000/abc",
        "pmid": 12345,
        "publication_pmc_id": "PMC123",
        "publication_date": "2024-02-29",
        "citations_received": 12,
        "_source": "legacy-source-b",
        "_run_id": "run-b",
        "_source_batch_id": "batch-b",
        "_original_id": "legacy-b",
    }
    changed_record = {
        "entity_id": "chembl:publication-c",
        "content_hash": "stale-c",
        "publication_id": "CHEMBL-PUB-1",
        "title": "Example Publication",
        "doi": "10.1000/abc",
        "publication_doi": "https://doi.org/10.1000/abc",
        "pmid": 12345,
        "publication_pmc_id": "PMC123",
        "publication_date": "2024-02-29",
        "citations_received": 13,
        "_source": "legacy-source-c",
        "_run_id": "run-c",
        "_source_batch_id": "batch-c",
        "_original_id": "legacy-c",
    }

    normalized_a = processor.normalize_record(record_a)
    normalized_b = processor.normalize_record(record_b)
    normalized_changed = processor.normalize_record(changed_record)

    assert normalized_a["title"] == "Example Publication"
    assert normalized_a["doi"] == "10.1000/abc"
    assert normalized_a["pmid"] == "12345"
    assert normalized_a["publication_pmc_id"] == "PMC123"
    assert normalized_a["publication_date"] == "2024-02-29"
    assert normalized_a["content_hash"] == normalized_b["content_hash"]
    assert normalized_changed["content_hash"] != normalized_a["content_hash"]


@pytest.mark.unit
def test_semanticscholar_publication_profile_makes_content_hash_invariant_for_equivalent_identifier_and_date_forms() -> (
    None
):
    processor = RecordNormalizationProcessor(
        provider="semanticscholar",
        entity_type="publication",
    )
    record_a = {
        "entity_id": "semanticscholar:publication-a",
        "content_hash": "stale-a",
        "paper_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "title": " Example <b>Publication</b> ",
        "doi": " HTTPS://doi.org/10.1000/ABC ",
        "pmid": " PMID:12345 ",
        "publication_date": "2024-02",
        "corpus_id": "42",
        "issue": " 7 ",
        "_source": "legacy-s2-a",
        "_run_id": "run-a",
    }
    record_b = {
        "entity_id": "semanticscholar:publication-b",
        "content_hash": "stale-b",
        "paper_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "title": "Example Publication",
        "doi": "10.1000/abc",
        "pmid": 12345,
        "publication_date": "2024-02-29",
        "corpus_id": 42.0,
        "issue": "7",
        "_source": "legacy-s2-b",
        "_run_id": "run-b",
    }
    changed_record = {
        "entity_id": "semanticscholar:publication-c",
        "content_hash": "stale-c",
        "paper_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "title": "Example Publication",
        "doi": "10.1000/abc",
        "pmid": 12345,
        "publication_date": "2024-02-29",
        "corpus_id": 43,
        "issue": "7",
        "_source": "legacy-s2-c",
        "_run_id": "run-c",
    }

    normalized_a = processor.normalize_record(record_a)
    normalized_b = processor.normalize_record(record_b)
    normalized_changed = processor.normalize_record(changed_record)

    assert normalized_a["title"] == "Example Publication"
    assert normalized_a["doi"] == "10.1000/abc"
    assert normalized_a["pmid"] == "12345"
    assert normalized_a["publication_date"] == "2024-02-29"
    assert normalized_a["corpus_id"] == 42
    assert normalized_a["issue"] == "7"
    assert normalized_a["content_hash"] == normalized_b["content_hash"]
    assert normalized_changed["content_hash"] != normalized_a["content_hash"]


@pytest.mark.unit
def test_chembl_target_profile_makes_content_hash_invariant_for_equivalent_numeric_anchor_forms() -> (
    None
):
    processor = RecordNormalizationProcessor(provider="chembl", entity_type="target")
    record_a = {
        "entity_id": "chembl:target-a",
        "content_hash": "stale-a",
        "target_id": " CHEMBL-TARGET-1 ",
        "pref_name": " Example <b>Target</b> ",
        "primary_component_id": "123.0",
        "taxonomy_id": "9606",
        "cross_references": '{"b":2,"a":1}',
        "_run_id": "run-a",
    }
    record_b = {
        "entity_id": "chembl:target-b",
        "content_hash": "stale-b",
        "target_id": "CHEMBL-TARGET-1",
        "pref_name": "Example Target",
        "primary_component_id": 123.0,
        "taxonomy_id": 9606.0,
        "cross_references": '{"a":1,"b":2}',
        "_run_id": "run-b",
    }

    normalized_a = processor.normalize_record(record_a)
    normalized_b = processor.normalize_record(record_b)

    assert normalized_a["pref_name"] == "Example Target"
    assert normalized_a["primary_component_id"] == pytest.approx(123.0)
    assert normalized_a["taxonomy_id"] == pytest.approx(9606.0)
    assert normalized_a["cross_references"] == '{"a":1,"b":2}'
    assert normalized_a["content_hash"] == normalized_b["content_hash"]


@pytest.mark.unit
def test_uniprot_idmapping_profile_makes_content_hash_invariant_for_equivalent_numeric_and_title_forms() -> (
    None
):
    processor = RecordNormalizationProcessor(
        provider="uniprot", entity_type="idmapping"
    )
    record_a = {
        "entity_id": "uniprot:idmapping-a",
        "content_hash": "stale-a",
        "target_id": " CHEMBL-TARGET-1 ",
        "protein_name": " Example <b>Protein</b> ",
        "annotation_score": "5",
        "sequence_length": "120",
        "sequence_mass": "12345",
        "taxonomy_id": "9606",
        "_run_id": "run-a",
    }
    record_b = {
        "entity_id": "uniprot:idmapping-b",
        "content_hash": "stale-b",
        "target_id": "CHEMBL-TARGET-1",
        "protein_name": "Example Protein",
        "annotation_score": 5,
        "sequence_length": 120,
        "sequence_mass": 12345,
        "taxonomy_id": 9606,
        "_run_id": "run-b",
    }

    normalized_a = processor.normalize_record(record_a)
    normalized_b = processor.normalize_record(record_b)

    assert normalized_a["protein_name"] == "Example Protein"
    assert normalized_a["annotation_score"] == 5
    assert normalized_a["sequence_length"] == 120
    assert normalized_a["sequence_mass"] == 12345
    assert normalized_a["content_hash"] == normalized_b["content_hash"]


@pytest.mark.unit
def test_pubmed_publication_profile_stabilizes_identifier_and_partial_dates() -> None:
    processor = RecordNormalizationProcessor(
        provider="pubmed", entity_type="publication"
    )

    normalized = processor.normalize_business_data(
        {
            "pmid": " PMID:12345 ",
            "pmc_id": " pmc123 ",
            "publication_date": "2024-01",
        }
    )

    assert normalized["pmid"] == "12345"
    assert normalized["pmc_id"] == "PMC123"
    assert normalized["publication_date"] == "2024-01-31"


@pytest.mark.unit
def test_pubmed_publication_profile_makes_content_hash_invariant_for_equivalent_identifier_date_and_set_like_forms() -> (
    None
):
    processor = RecordNormalizationProcessor(
        provider="pubmed", entity_type="publication"
    )
    record_a = {
        "entity_id": "pubmed:publication-a",
        "content_hash": "stale-a",
        "pmid": " PMID:12345 ",
        "pmc_id": " pmc123 ",
        "title": " Example <b>Publication</b> ",
        "publication_date": "2024-01",
        "pub_date": "2024-01",
        "issue": " 5 ",
        "volume": " 9 ",
        "subject_keywords": ["beta", "alpha"],
        "publication_types": ["Review", "Journal Article"],
        "_source": "legacy-pubmed-a",
        "_run_id": "run-a",
    }
    record_b = {
        "entity_id": "pubmed:publication-b",
        "content_hash": "stale-b",
        "pmid": 12345,
        "pmc_id": "PMC123",
        "title": "Example Publication",
        "publication_date": "2024-01-31",
        "pub_date": "2024-01-31",
        "issue": "5",
        "volume": "9",
        "subject_keywords": ["alpha", "beta"],
        "publication_types": ["Journal Article", "Review"],
        "_source": "legacy-pubmed-b",
        "_run_id": "run-b",
    }
    changed_record = {
        "entity_id": "pubmed:publication-c",
        "content_hash": "stale-c",
        "pmid": 12345,
        "pmc_id": "PMC123",
        "title": "Example Publication",
        "publication_date": "2024-01-31",
        "pub_date": "2024-01-31",
        "issue": "5",
        "volume": "9",
        "subject_keywords": ["alpha", "gamma"],
        "publication_types": ["Journal Article", "Review"],
        "_source": "legacy-pubmed-c",
        "_run_id": "run-c",
    }

    normalized_a = processor.normalize_record(record_a)
    normalized_b = processor.normalize_record(record_b)
    normalized_changed = processor.normalize_record(changed_record)

    assert normalized_a["pmid"] == "12345"
    assert normalized_a["pmc_id"] == "PMC123"
    assert normalized_a["publication_date"] == "2024-01-31"
    assert normalized_a["pub_date"] == "2024-01-31"
    assert normalized_a["issue"] == "5"
    assert normalized_a["volume"] == "9"
    assert normalized_a["content_hash"] == normalized_b["content_hash"]
    assert normalized_changed["content_hash"] != normalized_a["content_hash"]


@pytest.mark.unit
def test_pubchem_compound_profile_stabilizes_numeric_and_smiles_equivalence() -> None:
    processor = RecordNormalizationProcessor(provider="pubchem", entity_type="compound")

    normalized = processor.normalize_business_data(
        {
            "canonical_smiles": " C ",
            "molecular_weight": " 12.34000000001 ",
        }
    )

    assert normalized["canonical_smiles"] == "C"
    assert normalized["molecular_weight"] == pytest.approx(12.34)


_NEXT_WAVE_PROFILE_HASH_CASES = (
    pytest.param(
        "assay_parameters",
        {
            "entity_id": "chembl:assay-parameters-a",
            "content_hash": "stale-a",
            "assay_param_id": "12",
            "assay_id": "CHEMBL1",
            "type": " conc ",
            "value": "1.23000000001",
            "comments": '{"b":2,"a":1}',
            "standard_value": "5.5000",
            "standard_text_value": " ready ",
            "_run_id": "run-a",
        },
        {
            "entity_id": "chembl:assay-parameters-b",
            "content_hash": "stale-b",
            "assay_param_id": 12.0,
            "assay_id": "CHEMBL1",
            "type": "conc",
            "value": 1.23,
            "comments": '{"a":1,"b":2}',
            "standard_value": 5.5,
            "standard_text_value": "ready",
            "_run_id": "run-b",
        },
        {
            "assay_param_id": 12,
            "value": 1.23,
            "comments": '{"a":1,"b":2}',
            "standard_value": 5.5,
            "standard_text_value": "ready",
        },
        {
            "entity_id": "chembl:assay-parameters-c",
            "content_hash": "stale-c",
            "assay_param_id": 12,
            "assay_id": "CHEMBL1",
            "type": "conc",
            "value": 1.23,
            "comments": '{"a":1,"b":2}',
            "standard_value": 5.75,
            "standard_text_value": "ready",
            "_run_id": "run-c",
        },
        id="chembl-assay-parameters",
    ),
    pytest.param(
        "target_component",
        {
            "entity_id": "chembl:target-component-a",
            "content_hash": "stale-a",
            "component_id": "321",
            "accession": " P12345 ",
            "taxonomy_id": 9606.0,
            "target_component_xrefs": '{"b":2,"a":1}',
            "protein_classification_id": "42",
            "protein_classification_ids": " [42,7] ",
            "_run_id": "run-a",
        },
        {
            "entity_id": "chembl:target-component-b",
            "content_hash": "stale-b",
            "component_id": 321.0,
            "accession": "P12345",
            "taxonomy_id": 9606,
            "target_component_xrefs": '{"a":1,"b":2}',
            "protein_classification_id": 42.0,
            "protein_classification_ids": "[42,7]",
            "_run_id": "run-b",
        },
        {
            "component_id": 321,
            "taxonomy_id": 9606,
            "target_component_xrefs": '{"a":1,"b":2}',
            "protein_classification_id": 42,
            "protein_classification_ids": "[42,7]",
        },
        {
            "entity_id": "chembl:target-component-c",
            "content_hash": "stale-c",
            "component_id": 321,
            "accession": "Q99999",
            "taxonomy_id": 9606,
            "target_component_xrefs": '{"a":1,"b":2}',
            "protein_classification_id": 42,
            "protein_classification_ids": "[42,7]",
            "_run_id": "run-c",
        },
        id="chembl-target-component",
    ),
    pytest.param(
        "protein_class",
        {
            "entity_id": "chembl:protein-class-a",
            "content_hash": "stale-a",
            "protein_class_id": "7",
            "pref_name": " <b>Protein Kinase</b> ",
            "short_name": " <b>Class A</b> ",
            "class_level": "3",
            "sort_order": 4.0,
            "downgraded": "0",
            "_run_id": "run-a",
        },
        {
            "entity_id": "chembl:protein-class-b",
            "content_hash": "stale-b",
            "protein_class_id": 7.0,
            "pref_name": "Protein Kinase",
            "short_name": "Class A",
            "class_level": 3,
            "sort_order": "4",
            "downgraded": 0.0,
            "_run_id": "run-b",
        },
        {
            "protein_class_id": 7,
            "pref_name": "Protein Kinase",
            "short_name": "Class A",
            "class_level": 3,
            "sort_order": 4,
            "downgraded": 0,
        },
        {
            "entity_id": "chembl:protein-class-c",
            "content_hash": "stale-c",
            "protein_class_id": 7,
            "pref_name": "Ion Channel",
            "short_name": "Class A",
            "class_level": 3,
            "sort_order": 4,
            "downgraded": 0,
            "_run_id": "run-c",
        },
        id="chembl-protein-class",
    ),
    pytest.param(
        "cell_line",
        {
            "entity_id": "chembl:cell-line-a",
            "content_hash": "stale-a",
            "cell_id": "CHEMBL123",
            "cell_name": " <b>Human Fibroblast</b> ",
            "cell_source_tissue": " <b>Cervix</b> ",
            "cell_source_taxonomy_id": "9606",
            "_run_id": "run-a",
        },
        {
            "entity_id": "chembl:cell-line-b",
            "content_hash": "stale-b",
            "cell_id": "CHEMBL123",
            "cell_name": "Human Fibroblast",
            "cell_source_tissue": "Cervix",
            "cell_source_taxonomy_id": 9606.0,
            "_run_id": "run-b",
        },
        {
            "cell_name": "Human Fibroblast",
            "cell_source_tissue": "Cervix",
            "cell_source_taxonomy_id": 9606,
        },
        {
            "entity_id": "chembl:cell-line-c",
            "content_hash": "stale-c",
            "cell_id": "CHEMBL123",
            "cell_name": "Human Fibroblast",
            "cell_source_tissue": "Cervix",
            "cell_source_taxonomy_id": 10090,
            "_run_id": "run-c",
        },
        id="chembl-cell-line",
    ),
    pytest.param(
        "publication_similarity",
        {
            "entity_id": "chembl:publication-similarity-a",
            "content_hash": "stale-a",
            "sim_id": "8",
            "doc_1": "100",
            "doc_2": 200.0,
            "pubmed_id1": " PMID:12345 ",
            "pubmed_id2": 67890,
            "avg_tani": "0.50000000004",
            "max_tani": "0.8",
            "_run_id": "run-a",
        },
        {
            "entity_id": "chembl:publication-similarity-b",
            "content_hash": "stale-b",
            "sim_id": 8.0,
            "doc_1": 100,
            "doc_2": "200",
            "pubmed_id1": "12345",
            "pubmed_id2": "67890",
            "avg_tani": 0.5,
            "max_tani": 0.8,
            "_run_id": "run-b",
        },
        {
            "sim_id": 8,
            "doc_1": 100,
            "doc_2": 200,
            "pubmed_id1": "12345",
            "pubmed_id2": "67890",
            "avg_tani": 0.5,
            "max_tani": 0.8,
        },
        {
            "entity_id": "chembl:publication-similarity-c",
            "content_hash": "stale-c",
            "sim_id": 8,
            "doc_1": 100,
            "doc_2": 200,
            "pubmed_id1": "12345",
            "pubmed_id2": "67890",
            "avg_tani": 0.5,
            "max_tani": 0.9,
            "_run_id": "run-c",
        },
        id="chembl-publication-similarity",
    ),
    pytest.param(
        "compound_record",
        {
            "entity_id": "chembl:compound-record-a",
            "content_hash": "stale-a",
            "record_id": "77",
            "molecule_id": "CHEMBL25",
            "publication_id": "CHEMBL5",
            "src_id": "5",
            "compound_name": " <b>Sample Record</b> ",
            "_run_id": "run-a",
        },
        {
            "entity_id": "chembl:compound-record-b",
            "content_hash": "stale-b",
            "record_id": 77.0,
            "molecule_id": "CHEMBL25",
            "publication_id": "CHEMBL5",
            "src_id": 5.0,
            "compound_name": "Sample Record",
            "_run_id": "run-b",
        },
        {
            "record_id": 77,
            "src_id": 5,
            "compound_name": "Sample Record",
        },
        {
            "entity_id": "chembl:compound-record-c",
            "content_hash": "stale-c",
            "record_id": 77,
            "molecule_id": "CHEMBL25",
            "publication_id": "CHEMBL5",
            "src_id": 5,
            "compound_name": "Control Record",
            "_run_id": "run-c",
        },
        id="chembl-compound-record",
    ),
    pytest.param(
        "tissue",
        {
            "entity_id": "chembl:tissue-a",
            "content_hash": "stale-a",
            "tissue_id": "CHEMBL9001",
            "pref_name": " <b>Bone Marrow</b> ",
            "bto_id": "BTO:0000142",
            "_run_id": "run-a",
        },
        {
            "entity_id": "chembl:tissue-b",
            "content_hash": "stale-b",
            "tissue_id": "CHEMBL9001",
            "pref_name": "Bone Marrow",
            "bto_id": "BTO:0000142",
            "_run_id": "run-b",
        },
        {
            "pref_name": "Bone Marrow",
        },
        {
            "entity_id": "chembl:tissue-c",
            "content_hash": "stale-c",
            "tissue_id": "CHEMBL9001",
            "pref_name": "Bone Marrow",
            "bto_id": "BTO:0000999",
            "_run_id": "run-c",
        },
        id="chembl-tissue",
    ),
    pytest.param(
        "publication_term",
        {
            "entity_id": "chembl:publication-term-a",
            "content_hash": "stale-a",
            "publication_id": "CHEMBL5",
            "term": " <b>Kinase Inhibitor</b> ",
            "term_type": "KEYWORD",
            "mesh_id": " D001241 ",
            "_run_id": "run-a",
        },
        {
            "entity_id": "chembl:publication-term-b",
            "content_hash": "stale-b",
            "publication_id": "CHEMBL5",
            "term": "Kinase Inhibitor",
            "term_type": "KEYWORD",
            "mesh_id": "D001241",
            "_run_id": "run-b",
        },
        {
            "term": "Kinase Inhibitor",
            "mesh_id": "D001241",
        },
        {
            "entity_id": "chembl:publication-term-c",
            "content_hash": "stale-c",
            "publication_id": "CHEMBL5",
            "term": "Ion Channel",
            "term_type": "KEYWORD",
            "mesh_id": "D001241",
            "_run_id": "run-c",
        },
        id="chembl-publication-term",
    ),
    pytest.param(
        "subcellular_fraction",
        {
            "entity_id": "chembl:subcellular-fraction-a",
            "content_hash": "stale-a",
            "subcellular_fraction": " <b>Cell Membrane</b> ",
            "assay_count": "3",
            "example_assay_id": "CHEMBL1",
            "_run_id": "run-a",
        },
        {
            "entity_id": "chembl:subcellular-fraction-b",
            "content_hash": "stale-b",
            "subcellular_fraction": "Cell Membrane",
            "assay_count": 3.0,
            "example_assay_id": "CHEMBL1",
            "_run_id": "run-b",
        },
        {
            "subcellular_fraction": "Cell Membrane",
            "assay_count": 3,
        },
        {
            "entity_id": "chembl:subcellular-fraction-c",
            "content_hash": "stale-c",
            "subcellular_fraction": "Cell Membrane",
            "assay_count": 4,
            "example_assay_id": "CHEMBL1",
            "_run_id": "run-c",
        },
        id="chembl-subcellular-fraction",
    ),
)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("entity_type", "record_a", "record_b", "expected_fields", "changed_record"),
    _NEXT_WAVE_PROFILE_HASH_CASES,
)
def test_next_wave_profiles_have_deterministic_content_hash_regressions(
    entity_type: str,
    record_a: dict[str, object],
    record_b: dict[str, object],
    expected_fields: dict[str, object],
    changed_record: dict[str, object],
) -> None:
    processor = RecordNormalizationProcessor(provider="chembl", entity_type=entity_type)

    normalized_a = processor.normalize_record(record_a)
    normalized_b = processor.normalize_record(record_b)
    normalized_changed = processor.normalize_record(changed_record)

    assert processor.profile is not None
    for field_name, expected_value in expected_fields.items():
        assert normalized_a[field_name] == expected_value
        assert normalized_b[field_name] == expected_value
    assert normalized_a["content_hash"] == normalized_b["content_hash"]
    assert normalized_changed["content_hash"] != normalized_a["content_hash"]
