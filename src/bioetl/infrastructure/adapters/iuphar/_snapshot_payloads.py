"""Project catalog fields exclusively from verified frozen payload bytes."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace

from iuphar_target_class.matching import CatalogTarget
from iuphar_target_class.models import ProviderAnnotation
from iuphar_target_class.stage0.io import canonical_json_bytes

from ._manifest import decode_json, sha256


def identifier(value: object) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError("invalid provider target or taxonomy identifier")
    result = str(value)
    if not result.isascii() or not result.isdecimal() or result.startswith("0"):
        raise ValueError("invalid provider target or taxonomy identifier")
    return result


def _optional_text(row: Mapping[str, object], key: str) -> str | None:
    value = row.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"invalid provider text field: {key}")
    return value.strip()


def _strings(row: Mapping[str, object], key: str) -> tuple[str, ...]:
    value = row.get(key, [])
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ValueError(f"invalid provider string list: {key}")
    return tuple(dict.fromkeys(item.strip() for item in value))


def _target_payload(row: object) -> tuple[CatalogTarget, ProviderAnnotation]:
    if not isinstance(row, dict):
        raise ValueError("invalid provider target payload")
    target_id = identifier(row.get("targetId"))
    taxon = identifier(row.get("taxonId"))
    family_ids = row.get("familyIds", [])
    if not isinstance(family_ids, list):
        raise ValueError("invalid provider family list")
    families = tuple(identifier(value) for value in family_ids)
    name = _optional_text(row, "name")
    raw = canonical_json_bytes(row).decode("utf-8")
    catalog = CatalogTarget(
        target_id,
        _strings(row, "uniprotIds"),
        _optional_text(row, "geneSymbol"),
        _optional_text(row, "geneId"),
        taxon,
        (name,) if name is not None else (),
        _strings(row, "synonyms"),
    )
    annotation = ProviderAnnotation(
        target_id,
        _optional_text(row, "type"),
        families,
        sha256(raw.encode("utf-8")),
        taxon,
        raw,
    )
    return catalog, annotation


def parse_target_payloads(
    content: bytes,
) -> tuple[tuple[CatalogTarget, ...], dict[str, ProviderAnnotation]]:
    """Decode the declared gtopdb_target_payload_v1 frozen-source projection."""
    rows = decode_json(content)
    if not isinstance(rows, list) or not rows:
        raise ValueError("snapshot targets must be a nonempty JSON array")
    catalog: list[CatalogTarget] = []
    annotations: dict[str, ProviderAnnotation] = {}
    for row in rows:
        target, annotation = _target_payload(row)
        if target.target_id in annotations:
            raise ValueError("duplicate target identity in snapshot")
        catalog.append(target)
        annotations[target.target_id] = annotation
    return tuple(catalog), annotations


def parse_target_species_payloads(
    content: bytes,
) -> tuple[tuple[CatalogTarget, ...], dict[tuple[str, str], ProviderAnnotation]]:
    """Keep provider identity public while indexing annotations by target/species."""
    rows = decode_json(content)
    if not isinstance(rows, list) or not rows:
        raise ValueError("snapshot targets must be a nonempty JSON array")
    catalog: list[CatalogTarget] = []
    annotations: dict[tuple[str, str], ProviderAnnotation] = {}
    for row in rows:
        target, annotation = _target_payload(row)
        key = (target.target_id, target.species or "")
        if key in annotations:
            raise ValueError("duplicate target/species identity in snapshot")
        names = _strings(row, "names")
        catalog.append(
            replace(target, names=tuple(dict.fromkeys((*target.names, *names))))
        )
        annotations[key] = annotation
    return tuple(catalog), annotations
