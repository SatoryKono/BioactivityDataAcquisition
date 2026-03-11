"""Normalization and field extraction functions for bioactivity entity."""

from __future__ import annotations

from uuid import UUID

from bioetl.domain.types import BatchID, ContentHash, JsonDict, RunID

from ._converters import (
    _safe_float,
    _safe_int,
    _safe_json,
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
        "target_id": v
        if type(v := get("target_id")) is str
        else (None if v is None else str(v)),
        "assay_id": v
        if type(v := get("assay_id")) is str
        else (None if v is None else str(v)),
        "publication_id": v
        if type(v := get("publication_id")) is str
        else (None if v is None else str(v)),
        "record_id": v
        if type(v := get("record_id")) is int
        else (None if v is None else _safe_int(v)),
        "src_id": v
        if type(v := get("src_id")) is int
        else (None if v is None else _safe_int(v)),
    }


def _extract_molecule_fields(raw_data: JsonDict) -> dict[str, object]:
    get = raw_data.get
    return {
        "canonical_smiles": v
        if type(v := get("canonical_smiles")) is str
        else (None if v is None else str(v)),
        "molecule_pref_name": v
        if type(v := get("molecule_pref_name")) is str
        else (None if v is None else str(v)),
        "parent_molecule_id": v
        if type(v := get("parent_molecule_id")) is str
        else (None if v is None else str(v)),
    }


def _extract_target_fields(raw_data: JsonDict) -> dict[str, object]:
    get = raw_data.get
    return {
        "target_pref_name": v
        if type(v := get("target_pref_name")) is str
        else (None if v is None else str(v)),
        "target_organism": v
        if type(v := get("target_organism")) is str
        else (None if v is None else str(v)),
        "target_taxonomy_id": v
        if type(
            v := (
                get("target_taxonomy_id") or get("taxonomy_id") or get("target_tax_id")
            )
        )
        is int
        else (None if v is None else _safe_int(v)),
    }


def _extract_assay_fields(raw_data: JsonDict) -> dict[str, object]:
    get = raw_data.get
    return {
        "assay_type": v
        if type(v := get("assay_type")) is str
        else (None if v is None else str(v)),
        "assay_description": v
        if type(v := get("assay_description")) is str
        else (None if v is None else str(v)),
        "assay_variant_accession": v
        if type(v := get("assay_variant_accession")) is str
        else (None if v is None else str(v)),
        "assay_variant_mutation": v
        if type(v := get("assay_variant_mutation")) is str
        else (None if v is None else str(v)),
    }


def _extract_bao_fields(raw_data: JsonDict) -> dict[str, object]:
    get = raw_data.get
    return {
        "bao_endpoint": v
        if type(v := get("bao_endpoint")) is str
        else (None if v is None else str(v)),
        "bao_format": v
        if type(v := get("bao_format")) is str
        else (None if v is None else str(v)),
        "bao_label": v
        if type(v := get("bao_label")) is str
        else (None if v is None else str(v)),
    }


def _extract_activity_measurement_fields(raw_data: JsonDict) -> dict[str, object]:
    get = raw_data.get
    return {
        "type": v if type(v := get("type")) is str else (None if v is None else str(v)),
        "value": v
        if type(v := get("value")) is float
        else (None if v is None else _safe_float(v)),
        "units": v
        if type(v := get("units")) is str
        else (None if v is None else str(v)),
        "relation": v
        if type(v := get("relation")) is str
        else (None if v is None else str(v)),
        "upper_value": v
        if type(v := get("upper_value")) is float
        else (None if v is None else _safe_float(v)),
        "text_value": v
        if type(v := get("text_value")) is str
        else (None if v is None else str(v)),
        "standard_type": v
        if type(v := get("standard_type")) is str
        else (None if v is None else str(v)),
        "standard_value": v
        if type(v := get("standard_value")) is float
        else (None if v is None else _safe_float(v)),
        "standard_units": v
        if type(v := get("standard_units")) is str
        else (None if v is None else str(v)),
        "standard_relation": v
        if type(v := get("standard_relation")) is str
        else (None if v is None else str(v)),
        "standard_upper_value": v
        if type(v := get("standard_upper_value")) is float
        else (None if v is None else _safe_float(v)),
        "standard_text_value": v
        if type(v := get("standard_text_value")) is str
        else (None if v is None else str(v)),
        "standard_flag": v
        if type(v := get("standard_flag")) is int
        else (None if v is None else _safe_int(v)),
        "pchembl_value": v
        if type(v := get("pchembl_value")) is float
        else (None if v is None else _safe_float(v)),
    }


def _extract_publication_fields(raw_data: JsonDict) -> dict[str, object]:
    get = raw_data.get
    return {
        "journal": v
        if type(v := get("journal")) is str
        else (None if v is None else str(v)),
        "publication_doi": v
        if type(v := get("publication_doi")) is str
        else (None if v is None else str(v)),
        "publication_pmid": v
        if type(v := get("publication_pmid")) is str
        else (None if v is None else str(v)),
        "publication_pmc_id": v
        if type(v := get("publication_pmc_id")) is str
        else (None if v is None else str(v)),
        "publication_year": v
        if type(v := get("publication_year")) is int
        else (None if v is None else _safe_int(v)),
        "action_type": v
        if type(v := get("action_type")) is str
        else (None if v is None else str(v)),
        "action_type_description": v
        if type(v := get("action_type_description")) is str
        else (None if v is None else str(v)),
        "action_type_parent_type": v
        if type(v := get("action_type_parent_type")) is str
        else (None if v is None else str(v)),
    }


def _extract_quality_fields(raw_data: JsonDict) -> dict[str, object]:
    get = raw_data.get
    return {
        "activity_comment": v
        if type(v := get("activity_comment")) is str
        else (None if v is None else str(v)),
        "data_validity_comment": v
        if type(v := get("data_validity_comment")) is str
        else (None if v is None else str(v)),
        "data_validity_description": v
        if type(v := get("data_validity_description")) is str
        else (None if v is None else str(v)),
        "potential_duplicate": v
        if type(v := get("potential_duplicate")) is int
        else (None if v is None else _safe_int(v)),
        "manual_curation_flag": v
        if type(v := get("manual_curation_flag")) is int
        else (None if v is None else _safe_int(v)),
        "original_activity_id": v
        if type(v := get("original_activity_id")) is int
        else (None if v is None else _safe_int(v)),
        "activity_properties": _safe_json(get("activity_properties")),
        "toid": v
        if type(v := get("toid")) is int
        else (None if v is None else _safe_int(v)),
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
