"""Split normalization content-hash invariance tests."""

from __future__ import annotations

# ruff: noqa: F403,F405
from tests.unit.application.core.normalization_test_support import *


def test_profile_auto_resolves_for_chembl_publication_similarity() -> None:
    processor = build_normalization_processor(
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


def test_openalex_publication_profile_makes_content_hash_invariant_for_set_like_lists() -> (
    None
):
    processor = build_normalization_processor(
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


def test_uniprot_protein_profile_makes_content_hash_invariant_for_gene_synonym_order() -> (
    None
):
    processor = build_normalization_processor(
        provider="uniprot",
        entity_type="protein",
    )
    record_a = {
        "entity_id": "uniprot:1",
        "content_hash": "stale-a",
        "accession": "P12345",
        "protein_name": " Example <b>protein</b> ",
        "annotation_score": "5",
        "gene_synonyms": ["GENE2", "GENE1"],
        "taxonomy_id": "9606",
        "_run_id": "run-a",
    }
    record_b = {
        "entity_id": "uniprot:2",
        "content_hash": "stale-b",
        "accession": "P12345",
        "protein_name": "Example protein",
        "annotation_score": 5,
        "gene_synonyms": ["GENE1", "GENE2"],
        "taxonomy_id": 9606.0,
        "_run_id": "run-b",
    }
    changed_record = {
        "entity_id": "uniprot:3",
        "content_hash": "stale-c",
        "accession": "P12345",
        "protein_name": "Example protein",
        "annotation_score": 5,
        "gene_synonyms": ["GENE1", "GENE3"],
        "taxonomy_id": 9606,
        "_run_id": "run-c",
    }

    normalized_a = processor.normalize_record(record_a)
    normalized_b = processor.normalize_record(record_b)
    normalized_changed = processor.normalize_record(changed_record)

    assert normalized_a["protein_name"] == "Example protein"
    assert normalized_a["taxonomy_id"] == 9606
    assert normalized_a["content_hash"] == normalized_b["content_hash"]
    assert normalized_changed["content_hash"] != normalized_a["content_hash"]


def test_chembl_activity_profile_makes_content_hash_invariant_for_set_like_json_arrays() -> (
    None
):
    processor = build_normalization_processor(
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
    processor = build_normalization_processor(
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
    processor = build_normalization_processor(
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
    processor = build_normalization_processor(
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
    processor = build_normalization_processor(
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
    processor = build_normalization_processor(provider="pubchem")
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
    processor = build_normalization_processor(
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
@settings(suppress_health_check=[HealthCheck.too_slow])
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
    processor = build_normalization_processor(
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
    processor = build_normalization_processor(
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
def test_uniprot_idmapping_profile_treats_all_mappings_as_identifier_set() -> None:
    processor = build_normalization_processor(
        provider="uniprot", entity_type="idmapping"
    )

    record_a = {
        "target_id": "CHEMBL123",
        "mapping_status": "multiple",
        "all_mappings": ["P12345", "Q8N158"],
    }
    record_b = {
        "target_id": "CHEMBL123",
        "mapping_status": "multiple",
        "all_mappings": ["Q8N158", "P12345"],
    }

    normalized = processor.normalize_business_data(record_b)

    assert normalized["target_id"] == "CHEMBL123"
    assert normalized["all_mappings"] == '["P12345","Q8N158"]'
    assert processor.compute_content_hash(record_a) == processor.compute_content_hash(
        record_b
    )


@pytest.mark.unit
def test_uniprot_idmapping_profile_canonicalizes_taxonomy_id_through_reference_id_policy() -> (
    None
):
    processor = build_normalization_processor(
        provider="uniprot", entity_type="idmapping"
    )

    normalized = processor.normalize_business_data(
        {
            "target_id": "CHEMBL204",
            "mapping_status": "found",
            "taxonomy_id": " 09606 ",
        }
    )

    assert normalized["taxonomy_id"] == 9606


@pytest.mark.unit
def test_uniprot_protein_profile_treats_identifier_arrays_as_sets() -> None:
    processor = build_normalization_processor(provider="uniprot", entity_type="protein")

    record_a = {
        "accession": "P12345",
        "drugbank_ids": ["DB00002", "DB00001"],
        "chembl_ids": ["CHEMBL2", "CHEMBL1"],
        "reactome_xrefs": ["R-HSA-2", "R-HSA-1"],
    }
    record_b = {
        "accession": "P12345",
        "drugbank_ids": ["DB00001", "DB00002"],
        "chembl_ids": ["CHEMBL1", "CHEMBL2"],
        "reactome_xrefs": ["R-HSA-1", "R-HSA-2"],
    }

    assert processor.compute_content_hash(record_a) == processor.compute_content_hash(
        record_b
    )


@pytest.mark.unit
def test_uniprot_protein_profile_canonicalizes_taxonomy_id_through_reference_id_policy() -> (
    None
):
    processor = build_normalization_processor(provider="uniprot", entity_type="protein")

    normalized = processor.normalize_business_data(
        {
            "accession": "P12345",
            "taxonomy_id": " 09606 ",
        }
    )

    assert normalized["taxonomy_id"] == 9606


@pytest.mark.unit
def test_chembl_assay_profile_makes_content_hash_invariant_for_equivalent_scalar_and_json_forms() -> (
    None
):
    processor = build_normalization_processor(provider="chembl", entity_type="assay")
    record_a = {
        "entity_id": "chembl:assay-a",
        "content_hash": "stale-a",
        "assay_id": " CHEMBL-ASSAY-1 ",
        "target_id": " CHEMBL-TARGET-1 ",
        "assay_pref_name": " Example <b>Assay</b> ",
        "bao_format": "BAO:0000218",
        "bao_format_iri": None,
        "bao_format_mapping_status": None,
        "bao_ontology_version": None,
        "confidence_score": "7",
        "assay_taxonomy_id": "9606",
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
        "bao_format": "BAO_0000218",
        "bao_format_iri": "https://purl.obolibrary.org/obo/BAO_0000218",
        "bao_format_mapping_status": "mapped",
        "bao_ontology_version": "2.8.18a",
        "confidence_score": 7,
        "assay_taxonomy_id": 9606.0,
        "variant_sequence_json": '{"a":1,"b":2}',
        "_run_id": "run-b",
        "_source_batch_id": "batch-b",
    }

    normalized_a = processor.normalize_record(record_a)
    normalized_b = processor.normalize_record(record_b)

    assert normalized_a["assay_pref_name"] == "Example Assay"
    assert normalized_a["bao_format_mapping_status"] == "mapped"
    assert normalized_a["confidence_score"] == 7
    assert normalized_a["assay_taxonomy_id"] == pytest.approx(9606.0)
    assert normalized_a["variant_sequence_json"] == '{"a":1,"b":2}'
    assert normalized_a["content_hash"] == normalized_b["content_hash"]


@pytest.mark.unit
def test_chembl_publication_profile_makes_content_hash_invariant_for_equivalent_identifier_and_date_forms() -> (
    None
):
    processor = build_normalization_processor(
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
def test_semanticscholar_pub_content_hash_invariant_for_equivalent_id_and_date_forms() -> (
    None
):
    processor = build_normalization_processor(
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
    processor = build_normalization_processor(provider="chembl", entity_type="target")
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
    processor = build_normalization_processor(
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
    processor = build_normalization_processor(
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
def test_pubmed_pub_content_hash_invariant_for_equivalent_id_date_and_set_forms() -> (
    None
):
    processor = build_normalization_processor(
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
