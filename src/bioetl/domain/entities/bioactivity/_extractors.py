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
    get = raw_data.get
    return {
        "target_id": _safe_str(get("target_id")),
        "assay_id": _safe_str(get("assay_id")),
        "publication_id": _safe_str(get("publication_id")),
        "record_id": _safe_int(get("record_id")),
        "src_id": _safe_int(get("src_id")),
    }


def _extract_molecule_fields(raw_data: JsonDict) -> dict[str, object]:
    get = raw_data.get
    return {
        "canonical_smiles": _safe_str(get("canonical_smiles")),
        "molecule_pref_name": _safe_str(get("molecule_pref_name")),
        "parent_molecule_id": _safe_str(get("parent_molecule_id")),
    }


def _extract_target_fields(raw_data: JsonDict) -> dict[str, object]:
    get = raw_data.get
    return {
        "target_pref_name": _safe_str(get("target_pref_name")),
        "target_organism": _safe_str(get("target_organism")),
        "target_taxonomy_id": _safe_int(
            get("target_taxonomy_id") or get("taxonomy_id") or get("target_tax_id")
        ),
    }


def _extract_assay_fields(raw_data: JsonDict) -> dict[str, object]:
    get = raw_data.get
    return {
        "assay_type": _safe_str(get("assay_type")),
        "assay_description": _safe_str(get("assay_description")),
        "assay_variant_accession": _safe_str(get("assay_variant_accession")),
        "assay_variant_mutation": _safe_str(get("assay_variant_mutation")),
    }


def _extract_bao_fields(raw_data: JsonDict) -> dict[str, object]:
    get = raw_data.get
    return {
        "bao_endpoint": _safe_str(get("bao_endpoint")),
        "bao_format": _safe_str(get("bao_format")),
        "bao_label": _safe_str(get("bao_label")),
    }


def _extract_activity_measurement_fields(raw_data: JsonDict) -> dict[str, object]:
    get = raw_data.get
    return {
        "type": _safe_str(get("type")),
        "value": _safe_float(get("value")),
        "units": _safe_str(get("units")),
        "relation": _safe_str(get("relation")),
        "upper_value": _safe_float(get("upper_value")),
        "text_value": _safe_str(get("text_value")),
        "standard_type": _safe_str(get("standard_type")),
        "standard_value": _safe_float(get("standard_value")),
        "standard_units": _safe_str(get("standard_units")),
        "standard_relation": _safe_str(get("standard_relation")),
        "standard_upper_value": _safe_float(get("standard_upper_value")),
        "standard_text_value": _safe_str(get("standard_text_value")),
        "standard_flag": _safe_int(get("standard_flag")),
        "pchembl_value": _safe_float(get("pchembl_value")),
    }


def _extract_publication_fields(raw_data: JsonDict) -> dict[str, object]:
    get = raw_data.get
    return {
        "journal": _safe_str(get("journal")),
        "publication_doi": _safe_str(get("publication_doi")),
        "publication_pmid": _safe_str(get("publication_pmid")),
        "publication_pmc_id": _safe_str(get("publication_pmc_id")),
        "publication_year": _safe_int(get("publication_year")),
        "action_type": _safe_str(get("action_type")),
        "action_type_description": _safe_str(get("action_type_description")),
        "action_type_parent_type": _safe_str(get("action_type_parent_type")),
    }


def _extract_quality_fields(raw_data: JsonDict) -> dict[str, object]:
    get = raw_data.get
    return {
        "activity_comment": _safe_str(get("activity_comment")),
        "data_validity_comment": _safe_str(get("data_validity_comment")),
        "data_validity_description": _safe_str(get("data_validity_description")),
        "potential_duplicate": _safe_int(get("potential_duplicate")),
        "manual_curation_flag": _safe_int(get("manual_curation_flag")),
        "original_activity_id": _safe_int(get("original_activity_id")),
        "activity_properties": _safe_json(get("activity_properties")),
        "toid": _safe_int(get("toid")),
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
