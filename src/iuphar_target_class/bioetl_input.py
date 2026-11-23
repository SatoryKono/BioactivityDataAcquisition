"""Shared pure field projection for runtime classification and canonical export."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass

from iuphar_target_class.stage0.io import canonical_json_bytes

# v1 merged component accessions and UniProt xrefs into one required anchor.
UNIPROT_PROJECTION_POLICY_V1 = "iuphar-uniprot-merged-anchors-v1"
UNIPROT_PROJECTION_POLICY_V2 = "iuphar-uniprot-role-projection-v2"
_UNIPROT_ROLE_KEYS = (
    "component_accessions",
    "target_xref_uniprot_ids",
    "proven_uniprot_equivalents",
)

_TAXONOMY_ERROR = "taxonomy_id must be a positive integer"
_SOURCE_TAXA = {
    "Homo sapiens": "9606",
    "Mus musculus": "10090",
    "Rattus norvegicus": "10116",
}


def _text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return None if not text or text == "unknown" else text


def _tokens(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(part for item in value for part in _tokens(item))
    text = _text(value)
    if text is None:
        return ()
    if text.startswith("["):
        loaded = json.loads(text)
        if not isinstance(loaded, list):
            raise ValueError("expected a JSON identifier array")
        return _tokens(loaded)
    return tuple(part for raw in re.split(r"[|;]", text) if (part := _text(raw)))


def _taxon(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(_TAXONOMY_ERROR)
    if isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            raise ValueError(_TAXONOMY_ERROR)
        value = int(value)
    text = str(value).strip()
    if not text.isascii() or not text.isdecimal() or text.startswith("0"):
        raise ValueError(_TAXONOMY_ERROR)
    return text


def plain_target_value(value: object) -> object:
    """Normalize nested business payloads for shared runtime/export digests.

    Nullable Silver schema fields materialize as explicit ``None``; runtime
    classifier inputs omit the same keys. Dropping null-valued mapping entries
    keeps ``source_business_data`` identical across both paths.
    """
    if isinstance(value, Mapping):
        return {
            key: plain_target_value(item)
            for key, item in value.items()
            if item is not None
        }
    if isinstance(value, (list, tuple)):
        return [plain_target_value(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class UniprotIdentifierRoles:
    """Primary anchors, proven equivalents, and auxiliary cross-references.

    ``component_accessions`` are the primary UniProt identifiers of a single
    protein. On a complex or family the same accession names a component and
    does not prove the whole object. Proven equivalents are reliable anchors.
    ``target_xref_uniprot_ids`` stay auxiliary: an unknown xref is diagnostic,
    and every original accession is retained in ``evidence_ids``. Anchor order
    is not significant for the role sets; ``primary_ids`` keep first-seen order
    so the projected ``uniprot`` string stays stable for a given payload.
    """

    primary_ids: tuple[str, ...]
    equivalent_ids: tuple[str, ...]
    auxiliary_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    projection_policy: str = UNIPROT_PROJECTION_POLICY_V2


def _ordered(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def partition_uniprot_roles(data: Mapping[str, object]) -> UniprotIdentifierRoles:
    """Split UniProt links into required anchors and auxiliary evidence.

    Parameters
    ----------
    data : Mapping[str, object]
        Business payload. ``proven_uniprot_equivalents`` is optional.

    Returns
    -------
    UniprotIdentifierRoles
        Primary component accessions, declared equivalents, and xref-only ids.
        A value present as a primary accession is not repeated as auxiliary.
    """
    primary = _ordered(_tokens(data.get("component_accessions")))
    declared = _ordered(_tokens(data.get("proven_uniprot_equivalents")))
    xref = _ordered(_tokens(data.get("target_xref_uniprot_ids")))
    primary_ids = set(primary)
    equivalent = tuple(item for item in declared if item not in primary_ids)
    excluded = primary_ids | set(equivalent)
    auxiliary = tuple(item for item in xref if item not in excluded)
    evidence = tuple(sorted({*primary, *declared, *xref}))
    return UniprotIdentifierRoles(primary, equivalent, auxiliary, evidence)


def uniprot_roles_from_business_json(payload: object) -> UniprotIdentifierRoles | None:
    """Read role fields from stored business JSON, or skip historical rows.

    Kernel rows that only carry a merged ``uniprot`` string stay on the strict
    anchor API. A payload qualifies only when it still has the source fields.
    """
    if not isinstance(payload, str) or not payload.startswith("{"):
        return None
    try:
        loaded = json.loads(payload)
    except json.JSONDecodeError:
        return None
    if not isinstance(loaded, Mapping):
        return None
    if not any(key in loaded for key in _UNIPROT_ROLE_KEYS):
        return None
    return partition_uniprot_roles(loaded)


def project_target_fields(
    data: Mapping[str, object], taxon: str | None
) -> dict[str, str | None]:
    """Project classifier fields. ``uniprot`` is the primary accession list.

    Policy ``iuphar-uniprot-role-projection-v2`` no longer appends
    ``target_xref_uniprot_ids`` to the required anchor. Those values remain in
    ``source_business_data`` and in :func:`partition_uniprot_roles`.
    """
    accessions = partition_uniprot_roles(data).primary_ids
    synonyms = tuple(
        dict.fromkeys(
            (
                *_tokens(data.get("target_protein_synonyms")),
                *_tokens(data.get("target_gene_synonyms")),
            )
        )
    )
    return {
        "target_chembl_id": _text(data.get("target_id")),
        # ChEMBL identity is never passed as the kernel's explicit IUPHAR ID.
        "target_id": _text(data.get("iuphar_target_id")),
        "uniprot": "|".join(accessions) or None,
        "organism": taxon,
        "source_organism": _text(data.get("organism")),
        "name": _text(data.get("pref_name")),
        "synonyms": "|".join(synonyms) or None,
        "ec": "|".join(_tokens(data.get("target_ec_numbers"))) or None,
        "gene_symbol": _text(data.get("gene_symbol")),
        "gene_id": _text(data.get("gene_id")),
        "source_business_data": canonical_json_bytes(plain_target_value(data)).decode(
            "utf-8"
        ),
    }


def target_input_eligibility(
    data: Mapping[str, object], species: frozenset[str]
) -> tuple[str | None, str | None]:
    if data.get("target_type") != "SINGLE PROTEIN":
        return None, "unsupported_target_type"
    try:
        taxon = _taxon(data.get("taxonomy_id"))
    except ValueError:
        return None, "invalid_taxonomy_id"
    if taxon is not None and taxon not in species:
        return taxon, "unsupported_taxon"
    return taxon, _taxonomy_name_ineligibility(taxon, data.get("organism"))


def _taxonomy_name_ineligibility(taxon: str | None, organism: object) -> str | None:
    """Check name/taxonomy consistency after the species eligibility check."""
    source_taxon = _SOURCE_TAXA.get(_text(organism) or "")
    if source_taxon is None:
        return None
    if taxon is None:
        return "missing_taxonomy_for_known_organism"
    if taxon != source_taxon:
        return "taxonomy_name_conflict"
    return None


__all__ = [
    "UNIPROT_PROJECTION_POLICY_V1",
    "UNIPROT_PROJECTION_POLICY_V2",
    "UniprotIdentifierRoles",
    "partition_uniprot_roles",
    "plain_target_value",
    "project_target_fields",
    "target_input_eligibility",
    "uniprot_roles_from_business_json",
]
