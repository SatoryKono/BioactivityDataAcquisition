"""Profile normalizers for ChEMBL OBO ontology companion fields."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import NamedTuple

from bioetl.domain.normalization.chembl import (
    OntologyMappingResult,
    resolve_obo_ontology_companion_field,
)
from bioetl.domain.normalization.text import normalize_string
from bioetl.domain.schemas.constants import ONTOLOGY_MAPPING_STATUSES

__all__ = [
    "build_obo_companion_iri_normalizer",
    "build_obo_companion_mapping_status_normalizer",
    "build_obo_companion_version_normalizer",
]


class _OBOCompanionSpec(NamedTuple):
    source_field: str
    canonical_prefix: str
    ontology_version: str


def _record_string(record: Mapping[str, object] | None, key: str) -> str | None:
    if record is None:
        return None
    value = record.get(key)
    return value if isinstance(value, str) else None


def _resolve(
    record: Mapping[str, object] | None,
    spec: _OBOCompanionSpec,
) -> OntologyMappingResult:
    return resolve_obo_ontology_companion_field(
        _record_string(record, spec.source_field),
        canonical_prefix=spec.canonical_prefix,
        ontology_version=spec.ontology_version,
    )


def _normalize_mapping_status(value: object) -> object:
    if not isinstance(value, str):
        return None
    cleaned = normalize_string(value)
    if cleaned is None:
        return None
    candidate = cleaned.casefold()
    return candidate if candidate in ONTOLOGY_MAPPING_STATUSES else None


def build_obo_companion_iri_normalizer(
    *,
    source_field: str,
    canonical_prefix: str,
    ontology_version: str,
) -> Callable[..., object]:
    """Create a normalizer that derives an ontology IRI from a sibling ID field."""
    spec = _OBOCompanionSpec(source_field, canonical_prefix, ontology_version)

    def _normalizer(
        _value: object,
        *,
        record: Mapping[str, object] | None = None,
    ) -> object:
        return _resolve(record, spec=spec).iri

    _normalizer.__name__ = f"normalize_profile_{source_field}_companion_iri"
    return _normalizer


def build_obo_companion_mapping_status_normalizer(
    *,
    source_field: str,
    canonical_prefix: str,
    ontology_version: str,
) -> Callable[..., object]:
    """Create a normalizer that derives mapping status from a sibling ID field."""
    spec = _OBOCompanionSpec(source_field, canonical_prefix, ontology_version)

    def _normalizer(
        value: object,
        *,
        record: Mapping[str, object] | None = None,
    ) -> object:
        if record is None:
            return _normalize_mapping_status(value)
        return _resolve(record, spec=spec).status

    _normalizer.__name__ = (
        f"normalize_profile_{source_field}_companion_mapping_status"
    )
    return _normalizer


def build_obo_companion_version_normalizer(
    *,
    source_field: str,
    canonical_prefix: str,
    ontology_version: str,
) -> Callable[..., object]:
    """Create a normalizer that derives ontology version from a sibling ID field."""
    spec = _OBOCompanionSpec(source_field, canonical_prefix, ontology_version)

    def _normalizer(
        _value: object,
        *,
        record: Mapping[str, object] | None = None,
    ) -> object:
        return _resolve(record, spec=spec).ontology_version

    _normalizer.__name__ = f"normalize_profile_{source_field}_companion_version"
    return _normalizer
