"""Combine reviewed exact anchors with the official target catalog."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, replace

from .matching import HGNC, UNIPROT, CatalogTarget
from .models import ProviderAnnotation


@dataclass(frozen=True, slots=True)
class CatalogProjection:
    catalog: tuple[CatalogTarget, ...]
    annotations: dict[tuple[str, str], ProviderAnnotation]
    anchor_refs: dict[tuple[str, str, str, str], str]


def merge_reviewed_catalog(
    official: tuple[CatalogTarget, ...],
    official_annotations: Mapping[tuple[str, str], ProviderAnnotation],
    reviewed_catalog: tuple[CatalogTarget, ...],
    reviewed_annotations: Mapping[tuple[str, str], ProviderAnnotation],
) -> CatalogProjection:
    """Add reviewed anchors and variants while preserving official annotations."""
    catalog = {(row.target_id, row.species or ""): row for row in official}
    owners: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for row in official:
        for method, value in _anchor_pairs(row):
            owners[(row.species or "", method, value)].add(row.target_id)
    annotations = dict(official_annotations)
    anchor_refs = {}
    for target in reviewed_catalog:
        key = target.target_id, target.species or ""
        extra = _new_anchors(target, owners)
        if not extra:
            continue
        base = catalog.get(key)
        if base is None:
            # New variants supply exact anchors. Text uses official names.
            base = CatalogTarget(
                target.target_id, (), None, None, target.species, (), ()
            )
            annotations[key] = reviewed_annotations[key]
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
        raw_payload = reviewed_annotations[key].raw_payload
        if raw_payload is None:
            raise ValueError("reviewed supplemental target has no source payload")
        anchor_refs.update(
            {(*key, method, token): raw_payload for method, token in extra}
        )
    return CatalogProjection(tuple(catalog.values()), annotations, anchor_refs)


def _new_anchors(
    target: CatalogTarget, owners: Mapping[tuple[str, str, str], set[str]]
) -> tuple[tuple[str, str], ...]:
    pairs = _anchor_pairs(target)
    if not pairs:
        raise ValueError("reviewed supplemental target has no exact identity anchor")
    species = target.species or ""
    official_owners = {
        (method, token): owners.get((species, method, token), set())
        for method, token in pairs
    }
    if any(ids - {target.target_id} for ids in official_owners.values()):
        return ()
    return tuple(pair for pair, ids in official_owners.items() if not ids)


def _anchor_pairs(target: CatalogTarget) -> tuple[tuple[str, str], ...]:
    return (
        *((UNIPROT, accession.upper()) for accession in target.uniprot_ids),
        *((HGNC, value) for value in target.hgnc_ids),
    )
