"""Read independently curated additions to a frozen official projection."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, replace

from iuphar_target_class.identifier_roles import normalize_hgnc_ids
from iuphar_target_class.matching import HGNC, UNIPROT, CatalogTarget
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


@dataclass(frozen=True, slots=True)
class CatalogProjection:
    catalog: tuple[CatalogTarget, ...]
    annotations: dict[tuple[str, str], ProviderAnnotation]
    anchor_refs: dict[tuple[str, str, str, str], str]


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
        canonical_json_bytes(
            [
                {
                    **row,
                    "sourceSha256": hashes,
                    "reviewReference": text(row, "reviewReference"),
                }
                for row in supplemental
            ]
        )
    )
    targets = tuple(
        replace(target, hgnc_ids=normalize_hgnc_ids(hgnc_id))
        if target.species == "9606" and isinstance(hgnc_id := row.get("hgncId"), str)
        else target
        for target, row in zip(catalog, supplemental, strict=True)
    )
    return ReviewedInputs(targets, annotations, decisions, hashes)


def merge_reviewed_catalog(
    official: tuple[CatalogTarget, ...],
    official_annotations: Mapping[tuple[str, str], ProviderAnnotation],
    reviewed: ReviewedInputs,
) -> CatalogProjection:
    """Add reviewed anchors and variants while preserving official annotations."""
    catalog = {(row.target_id, row.species or ""): row for row in official}
    owners: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for row in official:
        for method, value in _anchor_pairs(row):
            owners[(row.species or "", method, value)].add(row.target_id)
    annotations = dict(official_annotations)
    anchor_refs = {}
    for target in reviewed.catalog:
        key = target.target_id, target.species or ""
        pairs = _anchor_pairs(target)
        if not pairs:
            raise ValueError(
                "reviewed supplemental target has no exact identity anchor"
            )
        if any(owners[(key[1], method, token)] - {key[0]} for method, token in pairs):
            continue
        extra = tuple(
            (method, token)
            for method, token in pairs
            if not owners[(key[1], method, token)]
        )
        if not extra:
            continue
        base = catalog.get(key)
        if base is None:
            # New variants supply exact anchors. Text uses official names.
            base = CatalogTarget(
                target.target_id, (), None, None, target.species, (), ()
            )
            annotations[key] = reviewed.annotations[key]
        catalog[key] = replace(
            base,
            uniprot_ids=(
                *base.uniprot_ids,
                *(token for method, token in extra if method == UNIPROT),
            ),
            hgnc_ids=(
                *base.hgnc_ids,
                *(token for method, token in extra if method == HGNC),
            ),
        )
        raw_payload = reviewed.annotations[key].raw_payload
        if raw_payload is None:
            raise ValueError("reviewed supplemental target has no source payload")
        anchor_refs.update(
            {(*key, method, token): raw_payload for method, token in extra}
        )
    return CatalogProjection(tuple(catalog.values()), annotations, anchor_refs)


def _anchor_pairs(target: CatalogTarget) -> tuple[tuple[str, str], ...]:
    return (
        *((UNIPROT, accession.upper()) for accession in target.uniprot_ids),
        *((HGNC, value) for value in target.hgnc_ids),
    )
