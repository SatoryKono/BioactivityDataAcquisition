"""Private profile normalizers for ChEMBL activity ontology companion fields."""

from __future__ import annotations

from collections.abc import Mapping

from bioetl.domain.normalization.chembl import (
    ActivityOntologyCompanionFields,
    resolve_activity_ontology_companion_fields,
)
from bioetl.domain.normalization.text import normalize_string

_ALLOWED_MAPPING_STATUSES = frozenset({"mapped", "unmapped", "missing"})


def _activity_ontology_companions(
    record: Mapping[str, object] | None,
) -> ActivityOntologyCompanionFields | None:
    if record is None:
        return None
    bao_endpoint = record.get("bao_endpoint")
    bao_format = record.get("bao_format")
    uo_units = record.get("uo_units")
    qudt_units = record.get("qudt_units")
    return resolve_activity_ontology_companion_fields(
        bao_endpoint=bao_endpoint if isinstance(bao_endpoint, str) else None,
        bao_format=bao_format if isinstance(bao_format, str) else None,
        uo_units=uo_units if isinstance(uo_units, str) else None,
        qudt_units=qudt_units if isinstance(qudt_units, str) else None,
    )


def _normalize_mapping_status(value: object) -> object:
    if not isinstance(value, str):
        return None
    cleaned = normalize_string(value)
    if cleaned is None:
        return None
    candidate = cleaned.casefold()
    return candidate if candidate in _ALLOWED_MAPPING_STATUSES else None


def normalize_profile_activity_bao_endpoint_iri(
    _value: object, *, record: Mapping[str, object] | None = None
) -> object:
    companions = _activity_ontology_companions(record)
    return None if companions is None else companions.bao_endpoint_iri


def normalize_profile_activity_bao_endpoint_mapping_status(
    value: object, *, record: Mapping[str, object] | None = None
) -> object:
    companions = _activity_ontology_companions(record)
    if companions is None:
        return _normalize_mapping_status(value)
    return companions.bao_endpoint_mapping_status


def normalize_profile_activity_bao_format_iri(
    _value: object, *, record: Mapping[str, object] | None = None
) -> object:
    companions = _activity_ontology_companions(record)
    return None if companions is None else companions.bao_format_iri


def normalize_profile_activity_bao_format_mapping_status(
    value: object, *, record: Mapping[str, object] | None = None
) -> object:
    companions = _activity_ontology_companions(record)
    if companions is None:
        return _normalize_mapping_status(value)
    return companions.bao_format_mapping_status


def normalize_profile_activity_bao_ontology_version(
    _value: object, *, record: Mapping[str, object] | None = None
) -> object:
    companions = _activity_ontology_companions(record)
    return None if companions is None else companions.bao_ontology_version


def normalize_profile_activity_uo_unit_iri(
    _value: object, *, record: Mapping[str, object] | None = None
) -> object:
    companions = _activity_ontology_companions(record)
    return None if companions is None else companions.uo_unit_iri


def normalize_profile_activity_uo_unit_mapping_status(
    value: object, *, record: Mapping[str, object] | None = None
) -> object:
    companions = _activity_ontology_companions(record)
    if companions is None:
        return _normalize_mapping_status(value)
    return companions.uo_unit_mapping_status


def normalize_profile_activity_uo_ontology_version(
    _value: object, *, record: Mapping[str, object] | None = None
) -> object:
    companions = _activity_ontology_companions(record)
    return None if companions is None else companions.uo_ontology_version


def normalize_profile_activity_qudt_unit_iri(
    _value: object, *, record: Mapping[str, object] | None = None
) -> object:
    companions = _activity_ontology_companions(record)
    return None if companions is None else companions.qudt_unit_iri


def normalize_profile_activity_qudt_unit_mapping_status(
    value: object, *, record: Mapping[str, object] | None = None
) -> object:
    companions = _activity_ontology_companions(record)
    if companions is None:
        return _normalize_mapping_status(value)
    return companions.qudt_unit_mapping_status


def normalize_profile_activity_qudt_ontology_version(
    _value: object, *, record: Mapping[str, object] | None = None
) -> object:
    companions = _activity_ontology_companions(record)
    return None if companions is None else companions.qudt_ontology_version
