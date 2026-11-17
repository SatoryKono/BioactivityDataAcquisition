"""Faithful species-aware projection of the official wide GtoPdb export."""

from __future__ import annotations

import csv
import io
import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import cast

from iuphar_target_class.iuphar_mapping import approved_class_mappings
from iuphar_target_class.stage0.io import canonical_json_bytes

from ._manifest import sha256
from ._snapshot_payloads import identifier
from .snapshot_evidence import SourceEvidence

SOURCE_FORMAT = "gtopdb_targets_csv_v1"
_FAMILY_ID = "Family id"
_FAMILY_NAME = "Family name"
_TARGET_ID = "Target id"
_TARGET_NAME = "Target name"
_StringList = list[str]
SPECIES_COLUMNS = {
    "9606": ("Human", "HGNC symbol"),
    "10116": ("Rat", "RGD symbol"),
    "10090": ("Mouse", "MGI symbol"),
}
_COMMON_COLUMNS = (
    "Type",
    _FAMILY_ID,
    _FAMILY_NAME,
    _TARGET_ID,
    _TARGET_NAME,
    "Subunit id",
    "Subunit name",
    "Target systematic name",
    "Target abbreviated name",
    "synonyms",
)


@dataclass(frozen=True, slots=True)
class OfficialProjection:
    targets: bytes
    audit: bytes
    allows_not_found: bool


def _read_export(raw: bytes, release: str) -> list[dict[str, str]]:
    stream = io.StringIO(raw.decode("utf-8-sig"), newline="")
    _require_release(stream, release)
    reader = csv.DictReader(stream, strict=True)
    _require_columns(reader.fieldnames or [])
    rows = list(reader)
    _require_rows(rows)
    return rows


def _require_release(stream: io.StringIO, release: str) -> None:
    first = next(csv.reader(stream, strict=True), [])
    version = (
        re.fullmatch(
            r"# GtoPdb Version:\s*(\S+)\s*-\s*published:\s*(\d{4}-\d{2}-\d{2})",
            first[0],
        )
        if len(first) == 1
        else None
    )
    if version is None or version.group(1) != release:
        raise ValueError("official export release header differs from acquisition")


def _require_columns(headers: Sequence[str]) -> None:
    required = {
        *_COMMON_COLUMNS,
        *(
            prefix + suffix
            for prefix, _ in SPECIES_COLUMNS.values()
            for suffix in (" SwissProt", " Entrez Gene")
        ),
        *(symbol for _, symbol in SPECIES_COLUMNS.values()),
    }
    if len(headers) != len(set(headers)) or not required.issubset(headers):
        raise ValueError("unsupported official GtoPdb CSV header")


def _require_rows(rows: list[dict[str, str]]) -> None:
    if not rows or any(
        None in row or any(value is None for value in row.values()) for row in rows
    ):
        raise ValueError("invalid official GtoPdb CSV rows")


def _groups(rows: list[dict[str, str]]) -> dict[str, list[tuple[int, dict[str, str]]]]:
    result: dict[str, list[tuple[int, dict[str, str]]]] = defaultdict(list)
    for record, row in enumerate(rows, 1):
        result[identifier(row[_TARGET_ID])].append((record, row))
    return dict(result)


def _selection(
    groups: Mapping[str, list[tuple[int, dict[str, str]]]], scope: Mapping[str, object]
) -> set[str]:
    selected = set(cast(_StringList, scope["included_target_ids"]))
    excluded = cast("list[dict[str, object]]", scope["excluded_targets"])
    excluded_ids = {str(item["target_id"]) for item in excluded}
    if selected.intersection(excluded_ids) or selected | excluded_ids != set(groups):
        raise ValueError(
            "reviewed selection must account for every raw provider identity"
        )
    for item in excluded:
        actual = [record for record, _ in groups[str(item["target_id"])]]
        if sorted(cast("list[int]", item["source_records"])) != actual:
            raise ValueError("exclusion ledger does not cover every raw source record")
    return selected


def _consistent(group: list[tuple[int, dict[str, str]]]) -> dict[str, str]:
    first = group[0][1]
    identity_columns = set(first) - {"Type", _FAMILY_ID, _FAMILY_NAME}
    if any(any(row[key] != first[key] for key in identity_columns) for _, row in group):
        raise ValueError("conflicting provider identity columns across family rows")
    if first["Subunit id"]:
        raise ValueError("subunit/complex target needs explicit reviewed exclusion")
    return first


def _tokens(value: str) -> list[str]:
    return list(
        dict.fromkeys(part.strip() for part in value.split("|") if part.strip())
    )


def _one(value: str) -> str | None:
    parts = _tokens(value)
    if len(parts) > 1:
        raise ValueError("multivalued species gene identity needs explicit resolution")
    return parts[0] if parts else None


def _variant(row: Mapping[str, str], taxon: str) -> dict[str, object] | None:
    prefix, symbol = SPECIES_COLUMNS[taxon]
    accessions = _tokens(row[prefix + " SwissProt"])
    gene_id, gene_symbol = _one(row[prefix + " Entrez Gene"]), _one(row[symbol])
    if not accessions and gene_id is None and gene_symbol is None:
        return None
    return {
        "targetId": identifier(row[_TARGET_ID]),
        "taxonId": taxon,
        "uniprotIds": accessions,
        "geneId": gene_id,
        "geneSymbol": gene_symbol,
        "name": row[_TARGET_NAME] or None,
        "names": [
            row[key]
            for key in (
                _TARGET_NAME,
                "Target systematic name",
                "Target abbreviated name",
            )
            if row[key]
        ],
        "synonyms": _tokens(row["synonyms"]),
    }


def _family_rows(
    group: list[tuple[int, dict[str, str]]], release: str
) -> list[dict[str, object]]:
    types, _ = approved_class_mappings(release)
    result: list[dict[str, object]] = []
    for record, row in group:
        if row["Type"] not in types:
            raise ValueError("unsupported official family type")
        result.append(
            {
                "familyId": identifier(row[_FAMILY_ID]),
                "familyName": row[_FAMILY_NAME],
                "familyType": row["Type"],
                "sourceRecord": record,
            }
        )
    return result


def _project_group(
    group: list[tuple[int, dict[str, str]]],
    species: list[str],
    release: str,
    raw_hash: str,
) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    row = _consistent(group)
    families = _family_rows(group, release)
    outputs: list[dict[str, object]] = []
    gaps: list[dict[str, str]] = []
    for taxon in species:
        variant = _variant(row, taxon)
        if variant is None:
            gaps.append({"target_id": row[_TARGET_ID], "taxon_id": taxon})
            continue
        outputs.append(
            {
                **variant,
                "familyIds": sorted({str(item["familyId"]) for item in families}),
                "familyRows": families,
                "source_sha256": raw_hash,
                "annotationCapability": "family_only",
            }
        )
    if not outputs:
        raise ValueError(
            "target without supported species identity needs explicit exclusion"
        )
    return outputs, gaps


def _raw_scope(
    evidence: SourceEvidence,
) -> tuple[
    bytes,
    list[dict[str, str]],
    dict[str, list[tuple[int, dict[str, str]]]],
    set[str],
    list[str],
]:
    if evidence.source_format != SOURCE_FORMAT or set(evidence.raw_artifacts) != {
        "targets_csv"
    }:
        raise ValueError("unsupported official export source format")
    raw = evidence.raw_artifacts["targets_csv"]
    rows = _read_export(raw, evidence.provider_release)
    groups = _groups(rows)
    scope = evidence.scope
    if (
        len(rows) != scope["expected_raw_row_count"]
        or len(groups) != scope["expected_provider_target_count"]
    ):
        raise ValueError("official raw denominator differs from reviewed scope")
    selected = _selection(groups, scope)
    species = cast(_StringList, scope["species_taxon_ids"])
    if not set(species).issubset(SPECIES_COLUMNS):
        raise ValueError(
            "official wide export supports only its explicit species columns"
        )
    return raw, rows, groups, selected, species


def project_official_export(evidence: SourceEvidence) -> OfficialProjection:
    """Preserve all raw rows; CSV Type is family evidence, never target type."""
    raw, rows, groups, selected, species = _raw_scope(evidence)
    scope = evidence.scope
    projected: list[dict[str, object]] = []
    uncovered: list[dict[str, str]] = []
    for target in sorted(selected, key=int):
        outputs, gaps = _project_group(
            groups[target], species, evidence.provider_release, sha256(raw)
        )
        projected.extend(outputs)
        uncovered.extend(gaps)
    if len(projected) != scope["expected_variant_count"]:
        raise ValueError("species variant count differs from reviewed scope")
    loaded_types = {row["Type"] for target in selected for _, row in groups[target]}
    if not set(cast(_StringList, scope["required_family_types"])).issubset(
        loaded_types
    ):
        raise ValueError("required reviewed family types are missing")
    audit = {
        "artifact": "bioetl_iuphar_projection_audit",
        "schema_version": 2,
        "annotation_capability": "family_only",
        "raw_row_count": len(rows),
        "raw_provider_target_count": len(groups),
        "included_provider_target_count": len(selected),
        "species_variant_count": len(projected),
        "uncovered_species": uncovered,
        "included_source_records": {
            target: [record for record, _ in groups[target]]
            for target in sorted(selected, key=int)
        },
        "excluded_targets": scope["excluded_targets"],
    }
    return OfficialProjection(
        canonical_json_bytes(projected),
        canonical_json_bytes(audit),
        not uncovered and not scope["excluded_targets"],
    )
