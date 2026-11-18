"""Additive, separately published candidates for a frozen target FK baseline.

This module never transforms provider records or writes to an input table.
New target rows must first pass the actual pipeline in an isolated data root.
"""

from __future__ import annotations

import hashlib
import shutil
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from urllib.parse import urlparse

import orjson
import pyarrow as pa
from deltalake import DeltaTable, write_deltalake

_TARGETS_JSON = "targets.json"
_STATUS_JSON = "status.json"
_ACQUISITION_JSON = "acquisition.json"
_RECOVERY_FILES = (_TARGETS_JSON, _STATUS_JSON, _ACQUISITION_JSON)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_bytes(value: object) -> bytes:
    return orjson.dumps(value, default=str, option=orjson.OPT_SORT_KEYS)


def _object(path: Path) -> dict[str, object]:
    value = orjson.loads(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return cast(dict[str, object], value)


def _ids(table: pa.Table) -> set[str]:
    values = table.column("target_id").to_pylist()
    if any(not isinstance(value, str) or not value for value in values):
        raise ValueError("Missing or invalid target_id")
    if len(set(values)) != len(values):
        raise ValueError("Duplicate target_id in target table")
    return set(values)


def _file_inventory(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): _sha256(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


@dataclass(frozen=True)
class FrozenDelta:
    """Delta version, actual partition-aware rows, and immutable byte inventory."""

    path: Path
    version: int
    table: pa.Table
    partition_columns: tuple[str, ...]
    files: Mapping[str, str]

    def verify_unchanged(self) -> None:
        """Reject concurrent log, parquet, schema, or version changes."""
        if DeltaTable(self.path).version() != self.version:
            raise ValueError(f"Delta version changed: {self.path}")
        if _file_inventory(self.path) != self.files:
            raise ValueError(f"Delta source bytes changed: {self.path}")

    def reference(self) -> dict[str, object]:
        """Return replayable baseline identity without claiming provider release."""
        return {
            "path": str(self.path),
            "version": self.version,
            "row_count": self.table.num_rows,
            "schema": str(self.table.schema),
            "schema_sha256": hashlib.sha256(self.table.schema.serialize()).hexdigest(),
            "partition_columns": list(self.partition_columns),
            "files": dict(self.files),
            "provider_release": "NOT_VERIFIED",
        }


def freeze_delta(path: Path) -> FrozenDelta:
    """Read a consistent Delta snapshot including partition values."""
    root = path.resolve(strict=True)
    files = _file_inventory(root)
    delta = DeltaTable(root)
    frozen = FrozenDelta(
        root,
        delta.version(),
        delta.to_pyarrow_table(),
        tuple(delta.metadata().partition_columns),
        files,
    )
    frozen.verify_unchanged()
    return frozen


@dataclass(frozen=True)
class TargetRepairBaseline:
    """All tables governing preservation and target FK closure."""

    silver: FrozenDelta
    gold: FrozenDelta
    assay: FrozenDelta

    @property
    def missing_ids(self) -> set[str]:
        """Return non-null assay target references absent from Gold."""
        refs = {x for x in self.assay.table.column("target_id").to_pylist() if x}
        return refs - _ids(self.gold.table)

    def verify_unchanged(self) -> None:
        """Check every source table again before publishing a candidate receipt."""
        for item in (self.silver, self.gold, self.assay):
            item.verify_unchanged()


def freeze_target_baseline(
    silver: Path, gold: Path, assay: Path
) -> TargetRepairBaseline:
    """Freeze existing target and referencing assay tables without writes."""
    result = TargetRepairBaseline(*(freeze_delta(p) for p in (silver, gold, assay)))
    _ids(result.silver.table)
    _ids(result.gold.table)
    if not result.missing_ids:
        raise ValueError("Baseline has no missing target references")
    if result.missing_ids & _ids(result.silver.table):
        raise ValueError("Recovery requires targets absent from both Silver and Gold")
    result.verify_unchanged()
    return result


@dataclass(frozen=True)
class RecoveredTargetSource:
    """Verified API response bytes and separate provider release provenance."""

    records: tuple[dict[str, object], ...]
    reference: Mapping[str, object]
    directory: Path
    files: Mapping[str, str]


def _check_receipt(entry: Mapping[str, object], path: Path) -> None:
    parsed = urlparse(str(entry.get("url", "")))
    if parsed.scheme != "https" or parsed.hostname != "www.ebi.ac.uk":
        raise ValueError("Recovery acquisition must identify the official ChEMBL API")
    if not parsed.path.startswith("/chembl/api/data/"):
        raise ValueError("Recovery acquisition is not a ChEMBL API request")
    if entry.get("http_status") != 200 or entry.get("bytes") != path.stat().st_size:
        raise ValueError(f"Unsuccessful or incomplete acquisition: {path}")
    if entry.get("sha256") != _sha256(path) or not entry.get("retrieved_at"):
        raise ValueError(f"Acquisition digest or timestamp mismatch: {path}")


def _read_acquisition(root: Path) -> dict[str, dict[str, object]]:
    receipts = orjson.loads((root / _ACQUISITION_JSON).read_bytes())
    if not isinstance(receipts, list) or len(receipts) != 2:
        raise ValueError("Expected exactly targets/status acquisition receipts")
    by_role = {
        entry.get("role"): entry for entry in receipts if isinstance(entry, dict)
    }
    if set(by_role) != {"targets", "status"}:
        raise ValueError("Missing or repeated acquisition role")
    for role in ("targets", "status"):
        _check_receipt(by_role[role], root / f"{role}.json")
    return cast(dict[str, dict[str, object]], by_role)


def _read_target_rows(root: Path, expected_ids: set[str]) -> list[dict[str, object]]:
    payload = _object(root / _TARGETS_JSON)
    records = payload.get("targets")
    page = payload.get("page_meta")
    if not isinstance(records, list) or not all(isinstance(x, dict) for x in records):
        raise ValueError("Invalid targets response")
    identifiers = [x.get("target_chembl_id") for x in records]
    if len(set(identifiers)) != len(records) or set(identifiers) != expected_ids:
        raise ValueError("Recovered targets must equal the exact missing FK cohort")
    if (
        not isinstance(page, dict)
        or page.get("next")
        or page.get("total_count") != len(records)
    ):
        raise ValueError("Recovery response is incomplete")
    return records


def read_recovered_target_source(
    directory: Path, *, expected_ids: set[str]
) -> RecoveredTargetSource:
    """Validate actual source bytes against receipts and the exact missing cohort."""
    root = directory.resolve(strict=True)
    acquisition = root / _ACQUISITION_JSON
    by_role = _read_acquisition(root)
    records = _read_target_rows(root, expected_ids)
    status = _object(root / _STATUS_JSON)
    release = status.get("chembl_db_version")
    if not isinstance(release, str) or not release.startswith("ChEMBL_"):
        raise ValueError("Provider release is unverified")
    return RecoveredTargetSource(
        tuple(records),
        {
            "provider": "chembl",
            "provider_release": release,
            "target_ids": sorted(expected_ids),
            "row_count": len(records),
            "acquisition": {"path": str(acquisition), "sha256": _sha256(acquisition)},
            "responses": {
                role: {"path": str(root / f"{role}.json"), **by_role[role]}
                for role in ("targets", "status")
            },
        },
        root,
        {name: _sha256(root / name) for name in _RECOVERY_FILES},
    )


def _add_rows(old: pa.Table, new: pa.Table) -> pa.Table:
    if _ids(old) & _ids(new):
        raise ValueError("Recovery would replace an existing target")
    schema = pa.unify_schemas([old.schema, new.schema])
    return pa.Table.from_pylist(old.to_pylist() + new.to_pylist(), schema=schema)


def _verify_old_rows(old: pa.Table, candidate: pa.Table) -> None:
    expected = {row["target_id"]: row for row in old.to_pylist()}
    actual = {
        row["target_id"]: row for row in candidate.select(old.column_names).to_pylist()
    }
    for target_id, row in expected.items():
        if _json_bytes(actual.get(target_id)) != _json_bytes(row):
            raise ValueError(f"Existing target changed: {target_id}")


def _read_additions(
    baseline: TargetRepairBaseline, isolated_data_root: Path
) -> dict[str, FrozenDelta]:
    additions = {
        layer: freeze_delta(isolated_data_root / "output" / layer / "chembl" / "target")
        for layer in ("silver", "gold")
    }
    for layer, item in additions.items():
        if _ids(item.table) != baseline.missing_ids:
            raise ValueError(
                f"Actual {layer} output did not retain every recovered target"
            )
    return additions


def _validate_destination(
    destination: Path,
    baseline: TargetRepairBaseline,
    additions: Mapping[str, FrozenDelta],
) -> Path:
    destination = destination.resolve()
    protected = [x.path for x in (baseline.silver, baseline.gold, baseline.assay)]
    protected.extend(x.path for x in additions.values())
    if any(
        destination.is_relative_to(p) or p.is_relative_to(destination)
        for p in protected
    ):
        raise ValueError("Candidate destination overlaps an input table")
    if destination.exists():
        raise ValueError("Candidate destination must be new")
    return destination


def _write_candidates(
    destination: Path,
    baseline: TargetRepairBaseline,
    tables: Mapping[str, pa.Table],
    additions: Mapping[str, FrozenDelta],
) -> dict[str, object]:
    destination.mkdir(parents=True)
    references: dict[str, object] = {}
    for layer, table in tables.items():
        previous = getattr(baseline, layer)
        path = destination / layer / "chembl" / "target"
        write_deltalake(path, table, partition_by=list(previous.partition_columns))
        actual = freeze_delta(path)
        _verify_old_rows(previous.table, actual.table)
        _verify_old_rows(additions[layer].table, actual.table)
        if _ids(actual.table) != _ids(previous.table) | baseline.missing_ids:
            raise ValueError("Written candidate cohort changed")
        references[layer] = actual.reference()
    return references


def _freeze_input_copies(
    destination: Path, baseline: TargetRepairBaseline, source: RecoveredTargetSource
) -> dict[str, object]:
    references: dict[str, object] = {}
    for layer in ("silver", "gold", "assay"):
        original = getattr(baseline, layer)
        copy_root = destination / "frozen-inputs" / layer
        for relative in original.files:
            target = copy_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original.path / relative, target)
        copied = freeze_delta(copy_root)
        if copied.files != original.files or copied.version != original.version:
            raise ValueError("Frozen baseline copy does not match original bytes")
        references[layer] = copied.reference()
    copy_root = destination / "frozen-inputs" / "source"
    copy_root.mkdir(parents=True)
    for name in _RECOVERY_FILES:
        shutil.copyfile(source.directory / name, copy_root / name)
    if _file_inventory(copy_root) != source.files:
        raise ValueError("Frozen acquisition bytes do not match original source pins")
    copied_source = read_recovered_target_source(
        copy_root, expected_ids=baseline.missing_ids
    )
    if copied_source.records != source.records:
        raise ValueError("Frozen recovery source does not match original rows")
    references["new_source"] = dict(copied_source.reference)
    return references


def publish_repair_candidate(
    baseline: TargetRepairBaseline,
    *,
    isolated_data_root: Path,
    destination: Path,
    source: RecoveredTargetSource,
    execution: Mapping[str, object],
) -> Path:
    """Publish additive candidates after actual isolated Silver/Gold execution.

    The completed manifest is written only after byte and row preservation,
    exact added-cohort equality, and assay-to-Gold FK closure all pass.
    """
    baseline.verify_unchanged()
    additions = _read_additions(baseline, isolated_data_root)
    destination = _validate_destination(destination, baseline, additions)
    tables = {
        layer: _add_rows(getattr(baseline, layer).table, additions[layer].table)
        for layer in ("silver", "gold")
    }
    refs = {x for x in baseline.assay.table.column("target_id").to_pylist() if x}
    if refs - _ids(tables["gold"]):
        raise ValueError("Assay target FK closure failed")
    references = _write_candidates(destination, baseline, tables, additions)
    frozen_inputs = _freeze_input_copies(destination, baseline, source)
    baseline.verify_unchanged()
    document = {
        "artifact": "bioetl_target_fk_repair_candidate",
        "schema_version": 1,
        "status": "validated_candidate",
        "contract_version": "3.0.0",
        "classification_mode": "off",
        "baseline": {
            name: getattr(baseline, name).reference()
            for name in ("silver", "gold", "assay")
        },
        "new_source": dict(source.reference),
        "frozen_inputs": frozen_inputs,
        "execution": dict(execution),
        "candidates": references,
        "added_target_ids": sorted(baseline.missing_ids),
        "checks": {
            "old_rows_and_hashes_preserved": True,
            "exact_additive_cohort": True,
            "assay_target_fk_closed": True,
            "source_tables_unchanged": True,
        },
        "limitations": [
            "Old provider release NOT_VERIFIED; new rows separately pinned",
            "Candidate only; no canonical table promotion",
        ],
    }
    manifest = destination / "manifest.json"
    temporary = manifest.with_name(".manifest.json.tmp")
    temporary.write_bytes(_json_bytes(document) + b"\n")
    temporary.replace(manifest)
    return manifest
