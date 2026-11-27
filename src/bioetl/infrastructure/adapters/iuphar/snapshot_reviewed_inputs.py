"""Read independently curated additions to a frozen official projection."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace

from iuphar_target_class.identifier_roles import normalize_hgnc_ids
from iuphar_target_class.matching import CatalogTarget
from iuphar_target_class.models import ProviderAnnotation
from iuphar_target_class.reviewed_classes import ReviewedClass, ReviewKey
from iuphar_target_class.stage0.io import canonical_json_bytes

from ._manifest import header, object_document, require_sha256, text
from ._snapshot_payloads import parse_target_species_payloads

_SOURCE_NAMES = frozenset({"_IUPHAR_target.csv", "_IUPHAR_family.csv"})


@dataclass(frozen=True, slots=True)
class ReviewedInputs:
    catalog: tuple[CatalogTarget, ...]
    annotations: Mapping[tuple[str, str], ProviderAnnotation]
    local_classes: Mapping[ReviewKey, ReviewedClass]
    source_hashes: Mapping[str, str]


def _rows(document: Mapping[str, object], key: str) -> list[dict[str, object]]:
    values = document.get(key)
    if not isinstance(values, list) or any(
        not isinstance(value, dict) for value in values
    ):
        raise ValueError(f"reviewed inputs require a list of objects: {key}")
    return values


def _validate_source_hashes(value: object) -> dict[str, str]:
    if not isinstance(value, dict) or value.keys() - _SOURCE_NAMES:
        raise ValueError("invalid reviewed supplemental source names")
    return {name: require_sha256(digest) for name, digest in value.items()}


def _family_payload(
    row: Mapping[str, object], hashes: Mapping[str, str]
) -> dict[str, object]:
    if row.get("type") is not None:
        raise ValueError(
            "reviewed supplemental payload must use family-only annotation"
        )
    return {
        **row,
        "sourceSha256": dict(hashes),
        "reviewReference": text(row, "reviewReference"),
    }


def parse_reviewed_inputs(raw: bytes) -> ReviewedInputs:
    document = object_document(raw)
    header(document, "bioetl_iuphar_reviewed_inputs")
    hashes = _validate_source_hashes(document.get("supplemental_source_sha256"))
    supplemental = _rows(document, "supplemental_targets")
    if supplemental and set(hashes) != _SOURCE_NAMES:
        raise ValueError(
            "supplemental targets require both reviewed CSV source digests"
        )
    decisions: dict[ReviewKey, ReviewedClass] = {}
    for row in _rows(document, "local_classes"):
        decision = ReviewedClass(
            text(row, "target_chembl_id"),
            text(row, "taxon"),
            text(row, "primary_uniprot"),
            text(row, "effective_class"),
            text(row, "origin"),
            text(row, "review_reference"),
        )
        if decision.key in decisions:
            raise ValueError("duplicate identity in reviewed class register")
        decisions[decision.key] = decision
    if not supplemental:
        return ReviewedInputs((), {}, decisions, hashes)
    catalog, annotations = parse_target_species_payloads(
        canonical_json_bytes([_family_payload(row, hashes) for row in supplemental])
    )
    targets = tuple(
        replace(target, hgnc_ids=normalize_hgnc_ids(hgnc_id))
        if target.species == "9606" and isinstance(hgnc_id := row.get("hgncId"), str)
        else target
        for target, row in zip(catalog, supplemental, strict=True)
    )
    if any(not (target.uniprot_ids or target.hgnc_ids) for target in targets):
        raise ValueError("reviewed supplemental target has no exact identity anchor")
    return ReviewedInputs(targets, annotations, decisions, hashes)
