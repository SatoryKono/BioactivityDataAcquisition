"""Pure normalization helpers for ChEMBL ontology, unit, and organism fields."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from bioetl.domain.normalization._chembl_organisms import (
    normalize_chembl_organism_name,
)
from bioetl.domain.normalization._chembl_units import (
    QUDT_ONTOLOGY_VERSION,
    QUDT_UNIT_IRI_TEMPLATE,
    resolve_qudt_unit_identifier,
)
from bioetl.domain.normalization._chembl_units import (
    normalize_qudt_unit as _normalize_qudt_unit,
)
from bioetl.domain.normalization._chembl_units import (
    normalize_standard_unit as _normalize_standard_unit,
)
from bioetl.domain.normalization.text import normalize_string

__all__ = [
    "ACTIVITY_ONTOLOGY_MAPPING_STATUSES",
    "ActivityOntologyCompanionFields",
    "OntologyMappingResult",
    "OntologyMappingStatus",
    "normalize_bao_identifier",
    "normalize_bao_label",
    "normalize_cellosaurus_id",
    "normalize_chembl_organism_name",
    "normalize_qudt_unit",
    "normalize_standard_unit",
    "normalize_uo_identifier",
    "resolve_activity_ontology_companion_fields",
]

_BAO_IDENTIFIER_RE = re.compile(r"^bao[_:](\d+)$", re.IGNORECASE)
_UO_IDENTIFIER_RE = re.compile(r"^uo[_:](\d+)$", re.IGNORECASE)
_BAO_CANONICAL_ID_RE = re.compile(r"^BAO_\d{7}$")
_UO_CANONICAL_ID_RE = re.compile(r"^UO_\d{7}$")
_CELLOSAURUS_IDENTIFIER_RE = re.compile(
    r"^cvcl[_:\-\s]?([a-z0-9]+)$",
    re.IGNORECASE,
)

OntologyMappingStatus = Literal["mapped", "unmapped", "missing"]
ACTIVITY_ONTOLOGY_MAPPING_STATUSES: tuple[OntologyMappingStatus, ...] = (
    "mapped",
    "unmapped",
    "missing",
)

BAO_ONTOLOGY_VERSION = "2.8.18a"
UO_ONTOLOGY_VERSION = "2026-01-16"
_OBO_IRI_TEMPLATE = "http://purl.obolibrary.org/obo/{identifier}"

_BAO_LABEL_BY_IDENTIFIER: dict[str, str] = {
    "BAO_0000019": "assay format",
    "BAO_0000219": "cell-based format",
    "BAO_0000221": "tissue-based format",
    "BAO_0000249": "cell membrane format",
    "BAO_0000251": "microsome format",
    "BAO_0000357": "single protein format",
    "BAO_0000366": "cell-free format",
}


@dataclass(frozen=True, slots=True)
class OntologyMappingResult:
    """Machine-readable result of resolving one ontology/unit token."""

    iri: str | None
    status: OntologyMappingStatus
    ontology_version: str | None


@dataclass(frozen=True, slots=True)
class ActivityOntologyCompanionFields:
    """Companion IRI/version/status fields for ChEMBL Activity rows."""

    bao_endpoint_iri: str | None
    bao_endpoint_mapping_status: OntologyMappingStatus
    bao_format_iri: str | None
    bao_format_mapping_status: OntologyMappingStatus
    bao_ontology_version: str | None
    uo_unit_iri: str | None
    uo_unit_mapping_status: OntologyMappingStatus
    uo_ontology_version: str | None
    qudt_unit_iri: str | None
    qudt_unit_mapping_status: OntologyMappingStatus
    qudt_ontology_version: str | None


def _normalize_prefixed_identifier(
    value: str | None,
    *,
    prefix: str,
    pattern: re.Pattern[str],
) -> str | None:
    """Canonicalize ontology identifiers to ``PREFIX_0000000`` form."""
    normalized = normalize_string(value)
    if normalized is None:
        return None

    match = pattern.fullmatch(normalized)
    if match is not None:
        return f"{prefix}_{match.group(1)}"

    if normalized.lower().startswith(prefix.lower()):
        return normalized.upper()
    return normalized


def normalize_bao_identifier(value: str | None) -> str | None:
    """Normalize BAO identifiers to canonical underscore form."""
    return _normalize_prefixed_identifier(
        value,
        prefix="BAO",
        pattern=_BAO_IDENTIFIER_RE,
    )


def normalize_bao_label(
    value: str | None,
    *,
    bao_identifier: str | None = None,
) -> str | None:
    """Normalize BAO labels using evidence-backed assay format mappings."""
    normalized_identifier = normalize_bao_identifier(bao_identifier)
    if normalized_identifier is not None:
        canonical_label = _BAO_LABEL_BY_IDENTIFIER.get(normalized_identifier)
        if canonical_label is not None:
            return canonical_label

    normalized = normalize_string(value)
    return normalized.lower() if normalized is not None else None


def normalize_uo_identifier(value: str | None) -> str | None:
    """Normalize Units Ontology identifiers to canonical underscore form."""
    return _normalize_prefixed_identifier(
        value,
        prefix="UO",
        pattern=_UO_IDENTIFIER_RE,
    )


def normalize_cellosaurus_id(value: str | None) -> str | None:
    """Normalize Cellosaurus identifiers to canonical ``CVCL_XXXX`` form."""
    normalized = normalize_string(value)
    if normalized is None:
        return None

    match = _CELLOSAURUS_IDENTIFIER_RE.fullmatch(normalized)
    if match is None:
        return normalized
    return f"CVCL_{match.group(1).upper()}"


def normalize_standard_unit(value: str | None) -> str | None:
    """Normalize standard unit names using the shared activity-unit rules."""
    return _normalize_standard_unit(value)


def normalize_qudt_unit(value: str | None) -> str | None:
    """Normalize QUDT values by trimming only."""
    return _normalize_qudt_unit(value)


def resolve_activity_ontology_companion_fields(
    *,
    bao_endpoint: str | None,
    bao_format: str | None,
    uo_units: str | None,
    qudt_units: str | None,
) -> ActivityOntologyCompanionFields:
    """Resolve ChEMBL Activity ontology/unit companion fields."""
    endpoint = _resolve_obo_identifier_mapping(
        normalize_bao_identifier(bao_endpoint),
        pattern=_BAO_CANONICAL_ID_RE,
        ontology_version=BAO_ONTOLOGY_VERSION,
    )
    assay_format = _resolve_obo_identifier_mapping(
        normalize_bao_identifier(bao_format),
        pattern=_BAO_CANONICAL_ID_RE,
        ontology_version=BAO_ONTOLOGY_VERSION,
    )
    uo = _resolve_obo_identifier_mapping(
        normalize_uo_identifier(uo_units),
        pattern=_UO_CANONICAL_ID_RE,
        ontology_version=UO_ONTOLOGY_VERSION,
    )
    qudt = _resolve_qudt_unit_mapping(qudt_units)

    return ActivityOntologyCompanionFields(
        bao_endpoint_iri=endpoint.iri,
        bao_endpoint_mapping_status=endpoint.status,
        bao_format_iri=assay_format.iri,
        bao_format_mapping_status=assay_format.status,
        bao_ontology_version=_shared_version(
            endpoint,
            assay_format,
            version=BAO_ONTOLOGY_VERSION,
        ),
        uo_unit_iri=uo.iri,
        uo_unit_mapping_status=uo.status,
        uo_ontology_version=uo.ontology_version,
        qudt_unit_iri=qudt.iri,
        qudt_unit_mapping_status=qudt.status,
        qudt_ontology_version=qudt.ontology_version,
    )


def _resolve_obo_identifier_mapping(
    value: str | None,
    *,
    pattern: re.Pattern[str],
    ontology_version: str,
) -> OntologyMappingResult:
    """Resolve an OBO-style ontology ID into an IRI and mapping status."""
    if value is None:
        return OntologyMappingResult(
            iri=None,
            status="missing",
            ontology_version=None,
        )
    if not pattern.fullmatch(value):
        return OntologyMappingResult(
            iri=None,
            status="unmapped",
            ontology_version=ontology_version,
        )
    return OntologyMappingResult(
        iri=_OBO_IRI_TEMPLATE.format(identifier=value),
        status="mapped",
        ontology_version=ontology_version,
    )


def _resolve_qudt_unit_mapping(value: str | None) -> OntologyMappingResult:
    """Resolve a QUDT unit token or legacy URI into a QUDT unit IRI."""
    normalized = normalize_qudt_unit(value)
    if normalized is None:
        return OntologyMappingResult(
            iri=None,
            status="missing",
            ontology_version=None,
        )

    qudt_identifier = resolve_qudt_unit_identifier(normalized)
    if qudt_identifier is None:
        return OntologyMappingResult(
            iri=None,
            status="unmapped",
            ontology_version=QUDT_ONTOLOGY_VERSION,
        )
    return OntologyMappingResult(
        iri=QUDT_UNIT_IRI_TEMPLATE.format(identifier=qudt_identifier),
        status="mapped",
        ontology_version=QUDT_ONTOLOGY_VERSION,
    )


def _shared_version(
    *results: OntologyMappingResult,
    version: str,
) -> str | None:
    """Return the family version when at least one field was present."""
    if all(result.status == "missing" for result in results):
        return None
    return version
