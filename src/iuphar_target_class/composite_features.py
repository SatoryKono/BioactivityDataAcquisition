"""RF-003 (#13311): post-join composite feature whitelist for classification.

Full UniProt annotations, idmapping accession, and ChEMBL protein-class L1/L2
summary exist only after composite dependency joins. This module projects a
bounded whitelist onto the offline kernel — never the full merged payload.
``predicted_l1`` / ``predicted_l2`` are ChEMBL protein-class hierarchy
predictions for local rules; they are not IUPHAR class identity by name.

Composite merge retains provider-qualified column names after ``seed_priority``
when a field has a single source (for example ``chembl.target.target_type``).
Lookup resolves short whitelist keys from qualified aliases before classify.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import MappingProxyType
from typing import Final

from iuphar_target_class.bioetl_input import plain_target_value
from iuphar_target_class.stage0.io import canonical_json_bytes

CONTRACT_VERSION: Final = "rf003-2026-11-24"
FEATURE_CONTRACT_VERSION: Final = CONTRACT_VERSION
SURFACE: Final = "composite_post_join"

# Kernel / business keys admitted into the classification input.
WHITELIST_FIELDS: Final[tuple[str, ...]] = (
    "target_id",
    "target_type",
    "taxonomy_id",
    "organism",
    "pref_name",
    "component_accessions",
    "target_xref_uniprot_ids",
    "target_ec_numbers",
    "target_protein_synonyms",
    "target_gene_synonyms",
    "uniprot_accession",
    "keywords",
    "gene_symbol",
    "gene_id",
    "gene_primary",
    "predicted_l1",
    "predicted_l2",
    "target_protein_class_name_L1",
    "target_protein_class_name_L2",
    "target_protein_class_id_L1",
    "target_protein_class_id_L2",
)

# Short key → preferred composite column names (short first, then qualified).
FIELD_ALIASES: Final[Mapping[str, tuple[str, ...]]] = MappingProxyType(
    {
        "target_id": ("target_id", "chembl.target.target_id", "target.target_id"),
        "target_type": (
            "target_type",
            "chembl.target.target_type",
            "target.target_type",
        ),
        "taxonomy_id": (
            "taxonomy_id",
            "chembl.target.taxonomy_id",
            "target.taxonomy_id",
        ),
        "organism": ("organism", "chembl.target.organism", "target.organism"),
        "pref_name": ("pref_name", "chembl.target.pref_name", "target.pref_name"),
        "component_accessions": (
            "component_accessions",
            "chembl.target.component_accessions",
            "target.component_accessions",
        ),
        "target_xref_uniprot_ids": (
            "target_xref_uniprot_ids",
            "chembl.target.target_xref_uniprot_ids",
            "target.target_xref_uniprot_ids",
        ),
        "target_ec_numbers": (
            "target_ec_numbers",
            "chembl.target.target_ec_numbers",
            "target.target_ec_numbers",
        ),
        "target_protein_synonyms": (
            "target_protein_synonyms",
            "chembl.target.target_protein_synonyms",
            "target.target_protein_synonyms",
        ),
        "target_gene_synonyms": (
            "target_gene_synonyms",
            "chembl.target.target_gene_synonyms",
            "target.target_gene_synonyms",
        ),
        "uniprot_accession": (
            "uniprot_accession",
            "uniprot.idmapping.uniprot_accession",
            "idmapping.uniprot_accession",
        ),
        "keywords": (
            "keywords",
            "uniprot.protein.keywords",
            "protein.keywords",
        ),
        "gene_symbol": ("gene_symbol",),
        "gene_id": ("gene_id",),
        "gene_primary": (
            "gene_primary",
            "uniprot.protein.gene_primary",
            "protein.gene_primary",
        ),
        "predicted_l1": ("predicted_l1",),
        "predicted_l2": ("predicted_l2",),
        "target_protein_class_name_L1": ("target_protein_class_name_L1",),
        "target_protein_class_name_L2": ("target_protein_class_name_L2",),
        "target_protein_class_id_L1": ("target_protein_class_id_L1",),
        "target_protein_class_id_L2": ("target_protein_class_id_L2",),
    }
)

FEATURE_SOURCES: Final[Mapping[str, tuple[str, ...]]] = MappingProxyType(
    {
        "ec": ("target_ec_numbers",),
        "keywords": ("keywords",),
        "predicted_l1": ("target_protein_class_name_L1", "predicted_l1"),
        "predicted_l2": ("target_protein_class_name_L2", "predicted_l2"),
        "taxon": ("taxonomy_id", "organism"),
        "identifiers": (
            "component_accessions",
            "target_xref_uniprot_ids",
            "uniprot_accession",
        ),
        "gene": ("gene_symbol", "gene_primary", "gene_id"),
    }
)

_L1_L2_PROVENANCE: Final = (
    "chembl_target_protein_classification_summary:predicted_layer_not_iuphar_identity"
)


def _text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        text = str(value).strip()
        return text or None
    if not isinstance(value, str):
        return None
    text = value.strip()
    return None if not text or text == "unknown" else text


def _present(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return _text(value) is not None
    if isinstance(value, (list, tuple, dict)):
        return bool(value)
    return True


def _lookup(row: Mapping[str, object], key: str) -> object | None:
    """Resolve a short whitelist key from short or provider-qualified columns."""
    for candidate in FIELD_ALIASES.get(key, (key,)):
        if candidate in row and _present(row[candidate]):
            return row[candidate]
    suffix = f".{key}"
    for column, value in row.items():
        if column.endswith(suffix) and _present(value):
            return value
    return None


def _digest(payload: object) -> str:
    return hashlib.sha256(canonical_json_bytes(plain_target_value(payload))).hexdigest()


def normalize_merged_row(row: Mapping[str, object]) -> dict[str, object]:
    """Project qualified composite columns onto short RF-003 whitelist keys."""
    normalized: dict[str, object] = {}
    for key in WHITELIST_FIELDS:
        value = _lookup(row, key)
        if value is not None:
            normalized[key] = value
    return normalized


def feature_availability(row: Mapping[str, object]) -> dict[str, bool]:
    """Report which whitelist feature groups are present on a merged row."""
    normalized = normalize_merged_row(row)
    return {
        name: any(_present(normalized.get(column)) for column in columns)
        for name, columns in FEATURE_SOURCES.items()
    }


def feature_completeness(row: Mapping[str, object]) -> str:
    """Return limited completeness without inventing missing optional features."""
    available = feature_availability(row)
    required = ("identifiers", "taxon")
    if not all(available[name] for name in required):
        return "incomplete"
    optional = ("ec", "keywords", "predicted_l1", "predicted_l2", "gene")
    if all(available[name] for name in optional):
        return "complete"
    return "partial"


def _predicted_layer(row: Mapping[str, object], *, level: int) -> str | None:
    explicit = _text(row.get(f"predicted_l{level}"))
    if explicit is not None:
        return explicit
    return _text(row.get(f"target_protein_class_name_L{level}"))


def _gene_symbol(row: Mapping[str, object]) -> str | None:
    return _text(row.get("gene_symbol")) or _text(row.get("gene_primary"))


def build_classification_business_data(
    row: Mapping[str, object],
    *,
    source_digests: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Project a merged composite row onto the RF-003 classification whitelist.

    ``source_business_data`` (via ``project_target_fields``) therefore carries
    only this bounded payload plus provenance digests — never the full merge.
    """
    normalized = normalize_merged_row(row)
    predicted_l1 = _predicted_layer(normalized, level=1)
    predicted_l2 = _predicted_layer(normalized, level=2)
    payload: dict[str, object] = {
        "target_id": normalized.get("target_id"),
        "target_type": normalized.get("target_type"),
        "taxonomy_id": normalized.get("taxonomy_id"),
        "organism": normalized.get("organism"),
        "pref_name": normalized.get("pref_name"),
        "component_accessions": normalized.get("component_accessions"),
        "target_xref_uniprot_ids": normalized.get("target_xref_uniprot_ids"),
        "target_ec_numbers": normalized.get("target_ec_numbers"),
        "target_protein_synonyms": normalized.get("target_protein_synonyms"),
        "target_gene_synonyms": normalized.get("target_gene_synonyms"),
        "uniprot_accession": normalized.get("uniprot_accession"),
        "keywords": normalized.get("keywords"),
        "gene_symbol": _gene_symbol(normalized),
        "gene_id": normalized.get("gene_id"),
        "predicted_l1": predicted_l1,
        "predicted_l2": predicted_l2,
        "_classification_surface": SURFACE,
        "_classification_feature_contract": FEATURE_CONTRACT_VERSION,
        "_classification_feature_completeness": feature_completeness(row),
        "_classification_l1_l2_provenance": _L1_L2_PROVENANCE,
    }
    digests = {
        "whitelist_sha256": _digest(
            {key: payload[key] for key in WHITELIST_FIELDS if key in payload}
        ),
        "availability_sha256": _digest(feature_availability(row)),
    }
    if source_digests:
        digests.update({key: value for key, value in source_digests.items() if value})
    payload["_classification_source_digests"] = digests
    return {key: value for key, value in payload.items() if value is not None}


def rows_missing_post_join_features(
    rows: Sequence[Mapping[str, object]],
) -> tuple[str, ...]:
    """Return target_ids that still lack optional post-join feature groups."""
    missing: list[str] = []
    for row in rows:
        availability = feature_availability(row)
        if availability["keywords"] or availability["predicted_l1"]:
            continue
        target_id = _text(normalize_merged_row(row).get("target_id"))
        if target_id is not None:
            missing.append(target_id)
    return tuple(missing)


def feature_whitelist_bytes() -> bytes:
    """Canonical bytes of the pinned RF-003 feature whitelist artifact."""
    path = Path("data/iuphar_target_class/rf003/feature_whitelist.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return (
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    ).encode("utf-8")


__all__ = [
    "CONTRACT_VERSION",
    "FEATURE_CONTRACT_VERSION",
    "FEATURE_SOURCES",
    "FIELD_ALIASES",
    "SURFACE",
    "WHITELIST_FIELDS",
    "build_classification_business_data",
    "feature_availability",
    "feature_completeness",
    "feature_whitelist_bytes",
    "normalize_merged_row",
    "rows_missing_post_join_features",
]
