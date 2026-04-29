"""Cross-layer normalization contracts for deterministic behavior."""

from __future__ import annotations

import pandas as pd
import pandera as pa
import pytest

from scripts.docs.generate_pipeline_normalization_field_matrix import (
    build_field_matrix_rows,
)
from bioetl.application.core.field_specs import (
    normalize_pmid as normalize_pmid_field_spec,
)
from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)
from bioetl.application.services.checkpoint_compatibility_service_v2 import (
    CheckpointCompatibilityServiceV2,
    CheckpointIdentity,
    CompatibilityVerdict,
    ExecutionPhase,
)
from bioetl.domain.normalization import (
    build_execution_identity_payload,
    compute_degraded_runtime_anchor_fingerprint,
    compute_execution_identity_fingerprint,
    normalize_doi,
    normalize_pmc_id,
    normalize_pmid,
    normalize_runtime_anchor_payload,
)
from bioetl.domain.normalization.json import canonicalize_json_string
from bioetl.domain.normalization.profiles import CHEMBL_ACTIVITY_PROFILE
from bioetl.domain.normalization.profiles.profile_normalizers import (
    normalize_profile_doi,
    normalize_profile_json_string_strict,
    normalize_profile_passthrough,
    normalize_profile_pmc_id,
    normalize_profile_pmid,
    normalize_profile_text,
)
from bioetl.domain.schemas.crossref.publication import PublicationEnrichedSchema
from bioetl.domain.schemas.pubmed.publication import PubMedPublicationSchema
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata
from bioetl.domain.value_objects import DOI
from bioetl.domain.value_objects.publications import PubMedId

pytestmark = [pytest.mark.contracts, pytest.mark.no_api]

_HASH_A = "a" * 64


def _matrix_row(pipeline_name: str, field_name: str) -> dict[str, str]:
    return next(
        row
        for row in build_field_matrix_rows()
        if row["pipeline_name"] == pipeline_name and row["field_name"] == field_name
    )


def test_pmid_contract_agrees_across_active_layers(
    minimal_pubmed_publication_df: pd.DataFrame,
) -> None:
    """PMID normalization must agree across helper, VO, schema, profile, and app."""
    raw_value = " 00012345 "
    expected = "12345"

    pubmed_processor = RecordNormalizationProcessor(
        provider="pubmed", entity_type="publication"
    )

    assert normalize_pmid(raw_value) == expected
    assert normalize_pmid_field_spec(raw_value) == expected
    assert normalize_profile_pmid(raw_value) == expected

    normalized_vo = PubMedId.from_raw(raw_value)
    assert normalized_vo is not None
    assert str(normalized_vo) == expected

    assert (
        pubmed_processor.normalize_business_data({"pmid": raw_value})["pmid"]
        == expected
    )

    schema_df = minimal_pubmed_publication_df.copy()
    schema_df["pmid"] = expected
    validated = PubMedPublicationSchema.validate(schema_df)
    assert validated["pmid"].iloc[0] == expected


def test_pmid_invalid_upper_bound_fails_across_active_layers(
    minimal_pubmed_publication_df: pd.DataFrame,
) -> None:
    """Oversized PMID values must fail closed across the same active seams."""
    oversized = "10000000000"

    pubmed_processor = RecordNormalizationProcessor(
        provider="pubmed", entity_type="publication"
    )

    assert normalize_pmid(oversized) is None
    assert normalize_pmid_field_spec(oversized) is None
    assert normalize_profile_pmid(oversized) is None
    assert PubMedId.from_raw(oversized) is None
    assert pubmed_processor.normalize_business_data({"pmid": oversized})["pmid"] is None

    schema_df = minimal_pubmed_publication_df.copy()
    schema_df["pmid"] = oversized
    with pytest.raises(pa.errors.SchemaError):
        PubMedPublicationSchema.validate(schema_df)


def test_doi_and_pmc_id_contracts_agree_across_active_layers(
    minimal_crossref_publication_df: pd.DataFrame,
) -> None:
    """DOI/PMC normalization should converge before schema and processor stages."""
    crossref_processor = RecordNormalizationProcessor(
        provider="crossref", entity_type="publication"
    )

    raw_doi = " https://doi.org/10.1000/XYZ "
    expected_doi = "10.1000/xyz"
    assert normalize_doi(raw_doi) == expected_doi
    assert normalize_profile_doi(raw_doi) == expected_doi
    normalized_doi = DOI.from_raw(raw_doi)
    assert normalized_doi is not None
    assert str(normalized_doi) == expected_doi
    assert (
        crossref_processor.normalize_business_data({"doi": raw_doi})["doi"]
        == expected_doi
    )

    doi_df = minimal_crossref_publication_df.copy()
    doi_df["doi"] = expected_doi
    doi_validated = PublicationEnrichedSchema.validate(doi_df)
    assert doi_validated["doi"].iloc[0] == expected_doi

    raw_pmc_id = " 12345 "
    expected_pmc_id = "PMC12345"
    assert normalize_pmc_id(raw_pmc_id) == expected_pmc_id
    assert normalize_profile_pmc_id(raw_pmc_id) == expected_pmc_id
    assert (
        crossref_processor.normalize_business_data({"pmc_id": raw_pmc_id})["pmc_id"]
        == expected_pmc_id
    )

    pmc_df = minimal_crossref_publication_df.copy()
    pmc_df["pmc_id"] = expected_pmc_id
    pmc_validated = PublicationEnrichedSchema.validate(pmc_df)
    assert pmc_validated["pmc_id"].iloc[0] == expected_pmc_id


def test_checkpoint_execution_identity_payload_matches_domain_contract() -> None:
    """Checkpoint metadata should emit the same canonical execution payload as the helper seam."""
    raw_inputs = {
        "pipeline_name": " chembl_activity ",
        "run_type": " INCREMENTAL ",
        "pipeline_version": " 1.2.3 ",
        "git_commit": " ABCDEF123 ",
        "effective_config_hash": f" SHA256:{_HASH_A.upper()} ",
        "dq_contract_compatibility_hash": " DEADBEEF ",
        "contract_ref": " ChemBL.Activity ",
        "contract_version": " v2 ",
        "effective_config_artifact_id": " artifact-42 ",
        "exact_replay": True,
        "input_snapshot_fingerprint": " FACE ",
    }
    expected_payload = build_execution_identity_payload(**raw_inputs)

    metadata = CheckpointMetadata(
        records_processed=1,
        pipeline_name=raw_inputs["pipeline_name"],
        run_type=raw_inputs["run_type"],
        pipeline_version=raw_inputs["pipeline_version"],
        git_commit=raw_inputs["git_commit"],
        effective_config_hash=raw_inputs["effective_config_hash"],
        dq_contract_compatibility_hash=raw_inputs["dq_contract_compatibility_hash"],
        contract_ref=raw_inputs["contract_ref"],
        contract_version=raw_inputs["contract_version"],
        effective_config_artifact_id=raw_inputs["effective_config_artifact_id"],
        exact_replay=raw_inputs["exact_replay"],
        input_snapshot_fingerprint=raw_inputs["input_snapshot_fingerprint"],
    )

    assert metadata.checkpoint_execution_identity_payload() == {
        key: value for key, value in expected_payload.items() if value is not None
    }
    assert (
        metadata.checkpoint_execution_identity_fingerprint()
        == compute_execution_identity_fingerprint(expected_payload)
    )


def test_runtime_anchor_service_path_matches_domain_degraded_fingerprint() -> None:
    """Service-level degraded runtime-anchor handling should match the domain seam."""
    service = CheckpointCompatibilityServiceV2()
    raw_current_payload = {
        "effective_config_hash": _HASH_A,
        "effective_config_artifact_id": " artifact-001 ",
        "contract_ref": " ChemBL.Activity ",
        "contract_version": " v1 ",
        "manifest_id": " manifest-a ",
    }
    expected_fingerprint = compute_degraded_runtime_anchor_fingerprint(
        normalize_runtime_anchor_payload(raw_current_payload)
    )

    current_identity = CheckpointIdentity(
        effective_config_hash=_HASH_A,
        execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
        checkpoint_schema_version="1.0.0",
        manifest_id=raw_current_payload["manifest_id"],
        contract_ref=raw_current_payload["contract_ref"],
        contract_version=raw_current_payload["contract_version"],
        effective_config_artifact_id=raw_current_payload[
            "effective_config_artifact_id"
        ],
    )
    checkpoint_identity = CheckpointIdentity(
        effective_config_hash=_HASH_A,
        execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
        checkpoint_schema_version="1.0.0",
        manifest_id="manifest-a",
        contract_ref="chembl.activity",
        contract_version="1.0.0",
        effective_config_artifact_id="artifact-001",
    )

    result = service.check_compatibility(current_identity, checkpoint_identity)

    assert result.verdict == CompatibilityVerdict.COMPATIBLE
    assert (
        result.details["execution_identity_compatibility"]["reason"]
        == "identical_degraded_runtime_anchor_fingerprint"
    )
    assert (
        result.details["current_identity"]["degraded_runtime_anchor_fingerprint"]
        == expected_fingerprint
    )
    assert (
        result.details["checkpoint_identity"]["degraded_runtime_anchor_fingerprint"]
        == expected_fingerprint
    )


def test_record_normalization_processor_keeps_equivalent_payloads_hash_stable() -> None:
    """Processor/profile path must collapse equivalent identifiers, JSON, and dates before hashing."""
    processor = RecordNormalizationProcessor(
        provider="crossref", entity_type="publication"
    )

    dirty_record = {
        "doi": " HTTPS://doi.org/10.1000/XYZ ",
        "pmid": " 00012345 ",
        "pmc_id": " 12345 ",
        "publication_date": "2024-03",
        "authors": ' [ "Alice" , "Bob" ] ',
        "title": "  Example publication  ",
        "journal": "  Test Journal  ",
    }
    clean_record = {
        "doi": "10.1000/xyz",
        "pmid": "12345",
        "pmc_id": "PMC12345",
        "publication_date": "2024-03-31",
        "authors": '["Alice","Bob"]',
        "title": "Example publication",
        "journal": "Test Journal",
    }

    normalized_dirty = processor.normalize_business_data(dirty_record)
    normalized_clean = processor.normalize_business_data(clean_record)

    assert normalized_dirty == normalized_clean
    assert normalized_dirty["authors"] == canonicalize_json_string(
        clean_record["authors"]
    )
    assert normalized_dirty["publication_date"] == "2024-03-31"
    assert processor.compute_content_hash(
        normalized_dirty
    ) == processor.compute_content_hash(normalized_clean)


def test_publication_set_like_json_fields_are_hash_order_invariant() -> None:
    """Set-like publication profile fields must not drift content_hash by array order."""
    processor = RecordNormalizationProcessor(
        provider="crossref", entity_type="publication"
    )

    record_a = processor.normalize_business_data(
        {
            "doi": "10.1000/example",
            "author_orcids": '["0000-0002", "0000-0001"]',
            "subject_keywords": '["kinase", "assay"]',
        }
    )
    record_b = processor.normalize_business_data(
        {
            "doi": "10.1000/example",
            "author_orcids": '["0000-0001", "0000-0002"]',
            "subject_keywords": '["assay", "kinase"]',
        }
    )

    assert record_a != record_b
    assert processor.compute_content_hash(record_a) == processor.compute_content_hash(
        record_b
    )


def test_chembl_publication_structured_json_fields_fail_closed_on_malformed_payloads() -> (
    None
):
    """Malformed JSON must not survive into strict ChEMBL publication fields."""
    processor = RecordNormalizationProcessor(
        provider="chembl", entity_type="publication"
    )

    normalized = processor.normalize_business_data(
        {
            "publication_id": "CHEMBL123",
            "title": "Example publication",
            "publication_type": "PUBLICATION",
            "authors": "{not json}",
            "affiliation_list": "{not json}",
            "author_orcids": "{not json}",
        }
    )

    assert normalized["publication_type"] == "journal-article"
    assert normalized["authors"] is None
    assert normalized["affiliation_list"] is None
    assert normalized["author_orcids"] is None


def test_chembl_publication_set_like_structured_json_fields_keep_hash_invariant() -> (
    None
):
    """Strict set-like JSON fields must stay hash-invariant across array permutations."""
    processor = RecordNormalizationProcessor(
        provider="chembl", entity_type="publication"
    )

    record_a = processor.normalize_business_data(
        {
            "publication_id": "CHEMBL123",
            "title": "Example publication",
            "publication_type": "PUBLICATION",
            "author_orcids": '["0000-0002", "0000-0001"]',
        }
    )
    record_b = processor.normalize_business_data(
        {
            "publication_id": "CHEMBL123",
            "title": "Example publication",
            "publication_type": "PUBLICATION",
            "author_orcids": '["0000-0001", "0000-0002"]',
        }
    )

    assert record_a["author_orcids"] != record_b["author_orcids"]
    assert processor.compute_content_hash(record_a) == processor.compute_content_hash(
        record_b
    )


def test_chembl_publication_aliases_keep_hash_stable_across_runtime_contract_fields() -> (
    None
):
    """publication_type and is_oa aliases must not create false content versions."""
    processor = RecordNormalizationProcessor(
        provider="chembl", entity_type="publication"
    )

    record_a = processor.normalize_business_data(
        {
            "publication_id": "CHEMBL123",
            "title": "Example publication",
            "publication_type": " PUBLICATION ",
            "is_oa": "1",
        }
    )
    record_b = processor.normalize_business_data(
        {
            "publication_id": "CHEMBL123",
            "title": "Example publication",
            "publication_type": "journal-article",
            "is_oa": True,
        }
    )

    assert record_a["publication_type"] == "journal-article"
    assert record_a["is_oa"] is True
    assert record_a == record_b
    assert processor.compute_content_hash(record_a) == processor.compute_content_hash(
        record_b
    )


def test_chembl_activity_units_and_target_organism_aliases_keep_hash_stable() -> None:
    """Controlled units and organism aliases must collapse before hashing."""
    processor = RecordNormalizationProcessor(provider="chembl", entity_type="activity")

    record_a = processor.normalize_business_data(
        {
            "activity_id": "1",
            "units": " μM ",
            "target_organism": "  homo   sapiens  ",
        }
    )
    record_b = processor.normalize_business_data(
        {
            "activity_id": "1",
            "units": "µM",
            "target_organism": "Homo sapiens",
        }
    )

    assert record_a["units"] == "µM"
    assert record_a["target_organism"] == "Homo sapiens"
    assert record_a == record_b
    assert processor.compute_content_hash(record_a) == processor.compute_content_hash(
        record_b
    )


def test_chembl_assay_bao_identifier_and_label_aliases_keep_hash_stable() -> None:
    """BAO labels must resolve inside the profile from sibling BAO identifiers."""
    processor = RecordNormalizationProcessor(provider="chembl", entity_type="assay")

    record_a = processor.normalize_business_data(
        {
            "assay_id": "CHEMBL123",
            "bao_format": " bao:0000357 ",
            "bao_format_iri": None,
            "bao_format_mapping_status": None,
            "bao_label": "  noisy label  ",
            "bao_ontology_version": None,
            "assay_type": "B",
        }
    )
    record_b = processor.normalize_business_data(
        {
            "assay_id": "CHEMBL123",
            "bao_format": "BAO_0000357",
            "bao_format_iri": "https://purl.obolibrary.org/obo/BAO_0000357",
            "bao_format_mapping_status": "mapped",
            "bao_label": "single protein format",
            "bao_ontology_version": "2.8.18a",
            "assay_type": "B",
        }
    )

    assert record_a["bao_format"] == "BAO_0000357"
    assert record_a["bao_format_mapping_status"] == "mapped"
    assert record_a["bao_format_iri"] == "https://purl.obolibrary.org/obo/BAO_0000357"
    assert record_a["bao_ontology_version"] == "2.8.18a"
    assert record_a["bao_label"] == "single protein format"
    assert record_a == record_b
    assert processor.compute_content_hash(record_a) == processor.compute_content_hash(
        record_b
    )


def test_chembl_target_component_organism_aliases_keep_hash_stable() -> None:
    """Target-component organism aliases must collapse to the shared canonical name."""
    processor = RecordNormalizationProcessor(
        provider="chembl",
        entity_type="target_component",
    )

    record_a = processor.normalize_business_data(
        {
            "component_id": "42",
            "organism": "e. coli",
        }
    )
    record_b = processor.normalize_business_data(
        {
            "component_id": "42",
            "organism": "Escherichia coli",
        }
    )

    assert record_a["organism"] == "Escherichia coli"
    assert record_a == record_b
    assert processor.compute_content_hash(record_a) == processor.compute_content_hash(
        record_b
    )


def test_chembl_cell_line_cellosaurus_aliases_keep_hash_stable() -> None:
    """Cellosaurus identifier formatting variants must hash identically."""
    processor = RecordNormalizationProcessor(
        provider="chembl",
        entity_type="cell_line",
    )

    record_a = processor.normalize_business_data(
        {
            "cell_id": "CHEMBL1",
            "cell_name": "HeLa",
            "cellosaurus_id": " cvcl:0030 ",
        }
    )
    record_b = processor.normalize_business_data(
        {
            "cell_id": "CHEMBL1",
            "cell_name": "HeLa",
            "cellosaurus_id": "CVCL_0030",
        }
    )

    assert record_a["cellosaurus_id"] == "CVCL_0030"
    assert record_a == record_b
    assert processor.compute_content_hash(record_a) == processor.compute_content_hash(
        record_b
    )


def test_chembl_tissue_obo_companion_aliases_keep_hash_stable() -> None:
    """OBO companion fields must resolve from normalized sibling IDs."""
    processor = RecordNormalizationProcessor(provider="chembl", entity_type="tissue")

    record_a = processor.normalize_business_data(
        {
            "tissue_id": "CHEMBL1",
            "pref_name": "Amniotic fluid",
            "bto_id": " bto:0000068 ",
            "bto_iri": None,
            "bto_mapping_status": None,
            "bto_ontology_version": None,
        }
    )
    record_b = processor.normalize_business_data(
        {
            "tissue_id": "CHEMBL1",
            "pref_name": "Amniotic fluid",
            "bto_id": "BTO_0000068",
            "bto_iri": "https://purl.obolibrary.org/obo/BTO_0000068",
            "bto_mapping_status": "mapped",
            "bto_ontology_version": "2026-01-16",
        }
    )

    assert record_a["bto_id"] == "BTO_0000068"
    assert record_a["bto_mapping_status"] == "mapped"
    assert record_a["bto_iri"] == "https://purl.obolibrary.org/obo/BTO_0000068"
    assert record_a["bto_ontology_version"] == "2026-01-16"
    assert record_a == record_b
    assert processor.compute_content_hash(record_a) == processor.compute_content_hash(
        record_b
    )


def test_profile_matrix_exposes_strict_json_semantics_for_chembl_structured_fields() -> (
    None
):
    """Field-matrix output must surface strict JSON semantics without reading profile code."""
    assay_parameters_row = _matrix_row("chembl_assay", "assay_parameters")
    publication_authors_row = _matrix_row("chembl_publication", "authors")

    assert assay_parameters_row["normalizer"] == "normalize_profile_json_string_strict"
    assert assay_parameters_row["strictness"] == "strict_json"
    assert (
        assay_parameters_row["dq_coverage"]
        == "runtime_warning:malformed_json_normalized_to_null"
    )
    assert (
        publication_authors_row["normalizer"] == "normalize_profile_json_string_strict"
    )
    assert publication_authors_row["strictness"] == "strict_json"
    assert (
        publication_authors_row["dq_coverage"]
        == "runtime_warning:malformed_json_normalized_to_null"
    )
    assert publication_authors_row["hash_ordering"] == "order_sensitive"


def test_profile_matrix_exposes_shared_chembl_policy_surfaces() -> None:
    """Field-matrix output must expose governed non-strict ChEMBL policy surfaces."""
    activity_units_row = _matrix_row("chembl_activity", "units")
    bao_format_row = _matrix_row("chembl_activity", "bao_format")
    publication_class_row = _matrix_row("chembl_publication", "publication_class")

    assert activity_units_row["semantic_category"] == "controlled_vocabulary"
    assert (
        activity_units_row["controlled_vocabulary_source"]
        == "configs/vocab/chembl_controlled.yaml"
    )

    assert bao_format_row["semantic_category"] == "ontology_reference_identifier"
    assert (
        bao_format_row["controlled_vocabulary_source"]
        == "configs/vocab/chembl_ontology.yaml"
    )

    assert publication_class_row["semantic_category"] == "derived_vocabulary"
    assert (
        publication_class_row["controlled_vocabulary_source"]
        == "configs/enums/publication_type_classification.csv"
    )


def test_profile_matrix_distinguishes_provider_universe_from_project_policy_scope() -> (
    None
):
    """Generated semantics must separate provider universes from project subsets."""
    assay_type_row = _matrix_row("chembl_activity", "assay_type")
    publication_term_type_row = _matrix_row("chembl_publication_term", "term_type")
    confidence_description_row = _matrix_row(
        "chembl_assay",
        "confidence_description",
    )

    assert assay_type_row["policy_scope"] == "project_subset_of_provider_universe"
    assert publication_term_type_row["policy_scope"] == "provider_full_universe"
    assert confidence_description_row["policy_scope"] == "provider_full_universe"


def test_chembl_publication_identifier_sidecars_stay_aligned_with_canonical_fields() -> (
    None
):
    """Duplicate publication identifier fields must normalize to one canonical value."""
    processor = RecordNormalizationProcessor(
        provider="chembl",
        entity_type="publication",
    )

    normalized = processor.normalize_business_data(
        {
            "publication_id": "CHEMBL123",
            "title": "Example publication",
            "publication_type": "PUBLICATION",
            "doi": " https://doi.org/10.1000/XYZ ",
            "publication_doi": "10.1000/xyz",
            "pmid": " 00012345 ",
            "publication_pmid": "12345",
        }
    )

    assert normalized["doi"] == "10.1000/xyz"
    assert normalized["publication_doi"] == "10.1000/xyz"
    assert normalized["pmid"] == "12345"
    assert normalized["publication_pmid"] == "12345"


def test_chembl_publication_raw_type_sidecar_is_explicitly_profiled() -> None:
    """Raw publication type must be an explicit chembl compatibility field."""
    processor = RecordNormalizationProcessor(
        provider="chembl",
        entity_type="publication",
    )

    normalized = processor.normalize_business_data(
        {
            "publication_id": "CHEMBL123",
            "title": "Example publication",
            "publication_type": "journal-article",
            "publication_type_raw": "PUBLICATION",
        }
    )

    assert normalized["publication_type"] == "journal-article"
    assert normalized["publication_type_raw"] == "PUBLICATION"


def test_chembl_publication_raw_type_sidecar_preserves_provider_semantics_separately() -> (
    None
):
    """Raw provider doc types must normalize independently from canonical publication taxonomy."""
    processor = RecordNormalizationProcessor(
        provider="chembl",
        entity_type="publication",
    )

    normalized = processor.normalize_business_data(
        {
            "publication_id": "CHEMBL124",
            "title": "Example dataset",
            "publication_type": "DATASET",
            "publication_type_raw": " dataset ",
        }
    )

    assert normalized["publication_type"] == "dataset"
    assert normalized["publication_type_raw"] == "DATASET"


def test_chembl_activity_meta_passthrough_contract_is_aligned_across_profile_matrix_and_processor() -> (
    None
):
    """chembl_activity meta fields must stay passthrough across all active seams."""
    processor = RecordNormalizationProcessor(provider="chembl", entity_type="activity")
    raw_run_id = "  run-001  "
    raw_entity_id = " entity-42 "

    assert (
        CHEMBL_ACTIVITY_PROFILE.rule_for("_run_id").normalizer
        is normalize_profile_passthrough
    )
    assert (
        CHEMBL_ACTIVITY_PROFILE.rule_for("entity_id").normalizer
        is normalize_profile_passthrough
    )

    run_id_row = _matrix_row("chembl_activity", "_run_id")
    entity_id_row = _matrix_row("chembl_activity", "entity_id")
    assert run_id_row["normalizer"] == "normalize_profile_passthrough"
    assert entity_id_row["normalizer"] == "normalize_profile_passthrough"
    assert run_id_row["include_in_content_hash"] == "false"
    assert entity_id_row["include_in_content_hash"] == "false"

    normalized = processor.normalize_business_data(
        {"_run_id": raw_run_id, "entity_id": raw_entity_id}
    )
    assert normalized["_run_id"] == raw_run_id
    assert normalized["entity_id"] == raw_entity_id


def test_chembl_activity_business_and_set_like_fields_follow_profile_family_contracts() -> (
    None
):
    """chembl_activity business text and set-like fields must align across profile/matrix/runtime."""
    processor = RecordNormalizationProcessor(provider="chembl", entity_type="activity")

    assert (
        CHEMBL_ACTIVITY_PROFILE.rule_for("activity_id").normalizer
        is normalize_profile_text
    )
    assert (
        CHEMBL_ACTIVITY_PROFILE.rule_for("activity_properties").normalizer
        is normalize_profile_json_string_strict
    )

    activity_id_row = _matrix_row("chembl_activity", "activity_id")
    activity_properties_row = _matrix_row("chembl_activity", "activity_properties")
    assert activity_id_row["normalizer"] == "normalize_profile_text"
    assert (
        activity_properties_row["normalizer"] == "normalize_profile_json_string_strict"
    )
    assert activity_properties_row["set_like"] == "true"
    assert activity_properties_row["strictness"] == "strict_json"

    normalized = processor.normalize_business_data(
        {
            "activity_id": "  ACT-001  ",
            "activity_properties": ' [ "beta" , "alpha" ] ',
        }
    )
    assert normalized["activity_id"] == "ACT-001"
    assert normalized["activity_properties"] == canonicalize_json_string(
        ' [ "beta" , "alpha" ] '
    )


def test_chembl_activity_standard_units_uses_the_same_unit_family_as_units() -> None:
    processor = RecordNormalizationProcessor(provider="chembl", entity_type="activity")

    standard_units_rule = CHEMBL_ACTIVITY_PROFILE.rule_for("standard_units")
    units_rule = CHEMBL_ACTIVITY_PROFILE.rule_for("units")

    assert standard_units_rule is not None
    assert units_rule is not None
    assert standard_units_rule.normalizer(" uM ") == "µM"
    assert units_rule.normalizer(" uM ") == "µM"

    standard_units_row = _matrix_row("chembl_activity", "standard_units")
    assert standard_units_row["normalizer"] == "normalize_profile_unit"
    assert standard_units_row["strictness"] == "controlled_unit"

    normalized = processor.normalize_business_data({"standard_units": " uM "})
    assert normalized["standard_units"] == "µM"


def test_chembl_publication_prefixed_identifiers_and_raw_type_are_schema_visible() -> (
    None
):
    publication_doi_row = _matrix_row("chembl_publication", "publication_doi")
    publication_pmid_row = _matrix_row("chembl_publication", "publication_pmid")
    publication_type_raw_row = _matrix_row("chembl_publication", "publication_type_raw")

    assert "domain_schema:present" in publication_doi_row["schema_coverage"]
    assert "domain_schema:present" in publication_pmid_row["schema_coverage"]
    assert "domain_schema:present" in publication_type_raw_row["schema_coverage"]


def test_chembl_target_controlled_json_arrays_are_set_like_for_hash_contracts() -> None:
    component_types_row = _matrix_row("chembl_target", "component_types")
    component_relationships_row = _matrix_row(
        "chembl_target", "component_relationships"
    )

    assert component_types_row["set_like"] == "true"
    assert component_types_row["hash_ordering"] == "set_like"
    assert component_relationships_row["set_like"] == "true"
    assert component_relationships_row["hash_ordering"] == "set_like"


def test_chembl_activity_set_like_json_fails_closed_on_malformed_payloads() -> None:
    """Malformed set-like JSON must still fail closed in strict ChEMBL activity fields."""
    processor = RecordNormalizationProcessor(provider="chembl", entity_type="activity")

    normalized = processor.normalize_business_data(
        {
            "activity_id": "ACT-001",
            "activity_properties": "{not json}",
        }
    )

    assert normalized["activity_properties"] is None
