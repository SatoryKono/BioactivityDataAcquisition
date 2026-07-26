"""Split next-wave deterministic normalization regression tests."""

from __future__ import annotations

import pytest

from tests.unit.application.core.normalization_test_support import *


pytestmark = pytest.mark.unit


def test_pubchem_compound_profile_stabilizes_numeric_and_smiles_equivalence() -> None:
    processor = build_normalization_processor(
        provider="pubchem", entity_type="compound"
    )

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
            "clo_id": "CLO:0003684",
            "clo_iri": None,
            "clo_mapping_status": None,
            "clo_ontology_version": None,
            "_run_id": "run-a",
        },
        {
            "entity_id": "chembl:cell-line-b",
            "content_hash": "stale-b",
            "cell_id": "CHEMBL123",
            "cell_name": "Human Fibroblast",
            "cell_source_tissue": "Cervix",
            "cell_source_taxonomy_id": 9606.0,
            "clo_id": "CLO_0003684",
            "clo_iri": "https://purl.obolibrary.org/obo/CLO_0003684",
            "clo_mapping_status": "mapped",
            "clo_ontology_version": "2026-01-16",
            "_run_id": "run-b",
        },
        {
            "cell_name": "Human Fibroblast",
            "cell_source_tissue": "Cervix",
            "cell_source_taxonomy_id": 9606,
            "clo_id": "CLO_0003684",
            "clo_iri": "https://purl.obolibrary.org/obo/CLO_0003684",
            "clo_mapping_status": "mapped",
            "clo_ontology_version": "2026-01-16",
        },
        {
            "entity_id": "chembl:cell-line-c",
            "content_hash": "stale-c",
            "cell_id": "CHEMBL123",
            "cell_name": "Human Fibroblast",
            "cell_source_tissue": "Cervix",
            "cell_source_taxonomy_id": 10090,
            "clo_id": "CLO_0003684",
            "clo_iri": "https://purl.obolibrary.org/obo/CLO_0003684",
            "clo_mapping_status": "mapped",
            "clo_ontology_version": "2026-01-16",
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
            "bto_iri": None,
            "bto_mapping_status": None,
            "bto_ontology_version": None,
            "_run_id": "run-a",
        },
        {
            "entity_id": "chembl:tissue-b",
            "content_hash": "stale-b",
            "tissue_id": "CHEMBL9001",
            "pref_name": "Bone Marrow",
            "bto_id": "BTO_0000142",
            "bto_iri": "https://purl.obolibrary.org/obo/BTO_0000142",
            "bto_mapping_status": "mapped",
            "bto_ontology_version": "2026-01-16",
            "_run_id": "run-b",
        },
        {
            "pref_name": "Bone Marrow",
            "bto_id": "BTO_0000142",
            "bto_iri": "https://purl.obolibrary.org/obo/BTO_0000142",
            "bto_mapping_status": "mapped",
            "bto_ontology_version": "2026-01-16",
        },
        {
            "entity_id": "chembl:tissue-c",
            "content_hash": "stale-c",
            "tissue_id": "CHEMBL9001",
            "pref_name": "Bone Marrow",
            "bto_id": "BTO_0000999",
            "bto_iri": "https://purl.obolibrary.org/obo/BTO_0000999",
            "bto_mapping_status": "mapped",
            "bto_ontology_version": "2026-01-16",
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
    processor = build_normalization_processor(
        provider="chembl", entity_type=entity_type
    )

    normalized_a = processor.normalize_record(record_a)
    normalized_b = processor.normalize_record(record_b)
    normalized_changed = processor.normalize_record(changed_record)

    assert processor.profile is not None
    for field_name, expected_value in expected_fields.items():
        assert normalized_a[field_name] == expected_value
        assert normalized_b[field_name] == expected_value
    assert normalized_a["content_hash"] == normalized_b["content_hash"]
    assert normalized_changed["content_hash"] != normalized_a["content_hash"]
