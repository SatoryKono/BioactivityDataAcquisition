"""Normalization and field extraction functions for bioactivity entity."""

from __future__ import annotations

from uuid import UUID

from bioetl.domain.types import BatchID, ContentHash, JsonDict, RunID

from ._converters import (
    _safe_float,
    _safe_int,
    _safe_json,
    _safe_str,
)


def _normalize_run_id(run_id: RunID | UUID) -> RunID:
    """Normalize input run identifier to domain RunID."""
    return RunID(run_id) if isinstance(run_id, UUID) else run_id


def _normalize_source_batch_id(source_batch_id: UUID | None) -> BatchID | None:
    """Normalize optional source batch identifier."""
    return BatchID(source_batch_id) if source_batch_id else None


def _build_content_hash(raw_data: JsonDict) -> ContentHash:
    """Build deterministic content hash from canonical JSON payload."""
    import hashlib

    from bioetl.domain.serialization import serialize_to_json_canonical

    content_hash_str = hashlib.sha256(
        serialize_to_json_canonical(raw_data).encode()
    ).hexdigest()
    return ContentHash(content_hash_str)


def _extract_optional_identifiers(raw_data: JsonDict) -> dict[str, object]:
    return {
        "target_id": _safe_str(raw_data.get("target_id")),
        "assay_id": _safe_str(raw_data.get("assay_id")),
        "publication_id": _safe_str(raw_data.get("publication_id")),
        "record_id": _safe_int(raw_data.get("record_id")),
        "src_id": _safe_int(raw_data.get("src_id")),
    }


def _extract_molecule_fields(raw_data: JsonDict) -> dict[str, object]:
    return {
        "canonical_smiles": _safe_str(raw_data.get("canonical_smiles")),
        "molecule_pref_name": _safe_str(raw_data.get("molecule_pref_name")),
        "parent_molecule_id": _safe_str(raw_data.get("parent_molecule_id")),
    }


def _extract_target_fields(raw_data: JsonDict) -> dict[str, object]:
    return {
        "target_pref_name": _safe_str(raw_data.get("target_pref_name")),
        "target_organism": _safe_str(raw_data.get("target_organism")),
        "target_taxonomy_id": _safe_int(
            raw_data.get("target_taxonomy_id")
            or raw_data.get("taxonomy_id")
            or raw_data.get("target_tax_id")
        ),
    }


def _extract_assay_fields(raw_data: JsonDict) -> dict[str, object]:
    return {
        "assay_type": _safe_str(raw_data.get("assay_type")),
        "assay_description": _safe_str(raw_data.get("assay_description")),
        "assay_variant_accession": _safe_str(raw_data.get("assay_variant_accession")),
        "assay_variant_mutation": _safe_str(raw_data.get("assay_variant_mutation")),
    }


def _extract_bao_fields(raw_data: JsonDict) -> dict[str, object]:
    return {
        "bao_endpoint": _safe_str(raw_data.get("bao_endpoint")),
        "bao_endpoint_iri": _safe_str(raw_data.get("bao_endpoint_iri")),
        "bao_endpoint_mapping_status": _safe_str(
            raw_data.get("bao_endpoint_mapping_status")
        ),
        "bao_format": _safe_str(raw_data.get("bao_format")),
        "bao_format_iri": _safe_str(raw_data.get("bao_format_iri")),
        "bao_format_mapping_status": _safe_str(
            raw_data.get("bao_format_mapping_status")
        ),
        "bao_label": _safe_str(raw_data.get("bao_label")),
        "bao_ontology_version": _safe_str(raw_data.get("bao_ontology_version")),
    }


def _extract_activity_measurement_fields(raw_data: JsonDict) -> dict[str, object]:
    return {
        "type": _safe_str(raw_data.get("type")),
        "value": _safe_float(raw_data.get("value")),
        "units": _safe_str(raw_data.get("units")),
        "relation": _safe_str(raw_data.get("relation")),
        "upper_value": _safe_float(raw_data.get("upper_value")),
        "text_value": _safe_str(raw_data.get("text_value")),
        "standard_type": _safe_str(raw_data.get("standard_type")),
        "standard_value": _safe_float(raw_data.get("standard_value")),
        "standard_units": _safe_str(raw_data.get("standard_units")),
        "standard_relation": _safe_str(raw_data.get("standard_relation")),
        "standard_upper_value": _safe_float(raw_data.get("standard_upper_value")),
        "standard_text_value": _safe_str(raw_data.get("standard_text_value")),
        "standard_flag": _safe_int(raw_data.get("standard_flag")),
        "pchembl_value": _safe_float(raw_data.get("pchembl_value")),
        "qudt_units": _safe_str(raw_data.get("qudt_units")),
        "qudt_unit_iri": _safe_str(raw_data.get("qudt_unit_iri")),
        "qudt_unit_mapping_status": _safe_str(
            raw_data.get("qudt_unit_mapping_status")
        ),
        "qudt_ontology_version": _safe_str(raw_data.get("qudt_ontology_version")),
        "uo_units": _safe_str(raw_data.get("uo_units")),
        "uo_unit_iri": _safe_str(raw_data.get("uo_unit_iri")),
        "uo_unit_mapping_status": _safe_str(raw_data.get("uo_unit_mapping_status")),
        "uo_ontology_version": _safe_str(raw_data.get("uo_ontology_version")),
    }


def _first_truthy_value(raw_data: JsonDict, *field_names: str) -> object | None:
    """Return the first truthy raw value across a set of alias fields."""
    for field_name in field_names:
        value = raw_data.get(field_name)
        if value:
            resolved_value: object = value
            return resolved_value
    return None


def _extract_publication_fields(raw_data: JsonDict) -> dict[str, object]:
    return {
        "journal": _safe_str(raw_data.get("journal")),
        "publication_year": _safe_int(raw_data.get("publication_year")),
        "publication_doi": _safe_str(
            _first_truthy_value(raw_data, "publication_doi", "doi", "document_doi")
        ),
        "publication_pmid": _safe_str(
            _first_truthy_value(
                raw_data,
                "publication_pmid",
                "pmid",
                "pubmed_id",
                "document_pubmed_id",
            )
        ),
        "publication_pmc_id": _safe_str(
            _first_truthy_value(
                raw_data,
                "publication_pmc_id",
                "pmc_id",
                "document_pmc_id",
            )
        ),
        "action_type": _safe_str(raw_data.get("action_type")),
        "action_type_description": _safe_str(raw_data.get("action_type_description")),
        "action_type_parent_type": _safe_str(raw_data.get("action_type_parent_type")),
    }


def _extract_quality_fields(raw_data: JsonDict) -> dict[str, object]:
    return {
        "activity_comment": _safe_str(raw_data.get("activity_comment")),
        "data_validity_comment": _safe_str(raw_data.get("data_validity_comment")),
        "data_validity_description": _safe_str(
            raw_data.get("data_validity_description")
        ),
        "potential_duplicate": _safe_int(raw_data.get("potential_duplicate")),
        "manual_curation_flag": _safe_int(raw_data.get("manual_curation_flag")),
        "original_activity_id": _safe_int(raw_data.get("original_activity_id")),
        "activity_properties": _safe_json(raw_data.get("activity_properties")),
        "toid": _safe_int(raw_data.get("toid")),
    }


def _extract_bioactivity_fields(raw_data: JsonDict) -> dict[str, object]:
    return (
        _extract_optional_identifiers(raw_data)
        | _extract_molecule_fields(raw_data)
        | _extract_target_fields(raw_data)
        | _extract_assay_fields(raw_data)
        | _extract_bao_fields(raw_data)
        | _extract_activity_measurement_fields(raw_data)
        | _extract_publication_fields(raw_data)
        | _extract_quality_fields(raw_data)
    )
