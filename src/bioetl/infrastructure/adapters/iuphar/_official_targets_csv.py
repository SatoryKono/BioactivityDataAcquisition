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


from ._official_target_projection import project_official_export
