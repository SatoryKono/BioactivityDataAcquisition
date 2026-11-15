"""Import and render the target-class batch without rewriting source data."""

from __future__ import annotations

import csv
import hashlib
import io
import re
from collections.abc import Mapping
from dataclasses import asdict
from pathlib import Path
from types import MappingProxyType

from .delivery import _create_new, _path_inside_root, result_names
from .models import RawTargetRow, RunProvenance
from .pipeline import BatchResult, IndexedSnapshot, RowResult, classify_batch
from .stage0.io import canonical_json_bytes


def read_legacy_batch(content: bytes) -> tuple[RawTargetRow, ...]:
    """Decode a CSV, retaining original legacy class only as a source field."""
    stream = io.StringIO(content.decode("utf-8-sig"), newline="")
    reader = csv.DictReader(stream, strict=True)
    headers = reader.fieldnames or []
    if len(headers) != len(set(headers)) or not {
        "input_row_id",
        "target_kind",
    }.issubset(headers):
        raise ValueError("invalid CSV header: expected unique columns and row ID/kind")
    rows: list[RawTargetRow] = []
    for row in reader:
        if None in row or any(value is None for value in row.values()):
            raise ValueError("invalid CSV row width")
        fields = {
            k: v for k, v in row.items() if k not in {"input_row_id", "target_kind"}
        }
        rows.append(RawTargetRow(row["input_row_id"], fields, row["target_kind"]))
    return tuple(rows)


def read_chembl_target_csv_v1(
    content: bytes, *, source_path: str, target_kind: str
) -> tuple[RawTargetRow, ...]:
    """Adapt the pinned project export with an explicitly approved row kind.

    No ChEMBL identifier becomes an IUPHAR ID and no species/kind is guessed.
    All source columns and byte/record provenance remain alongside aliases.
    """
    if not source_path or target_kind not in {"protein", "complex"}:
        raise ValueError(
            "project CSV import requires a source and explicit target kind"
        )
    reader = csv.DictReader(
        io.StringIO(content.decode("utf-8-sig"), newline=""), strict=True
    )
    expected = (
        "target_chembl_id",
        "isoform_ids",
        "isoform_names",
        "isoforms",
        "organism",
        "pH_dependence",
        "primaryAccession",
        "target_names",
        "target_uniprot_id",
    )
    if tuple(reader.fieldnames or ()) != expected:
        raise ValueError("invalid chembl_target_csv_v1 header")
    digest = hashlib.sha256(content).hexdigest()
    identity = hashlib.sha256(source_path.encode("utf-8")).hexdigest()
    rows = []
    for record, raw in enumerate(reader, 1):
        if None in raw or any(value is None for value in raw.values()):
            raise ValueError("invalid CSV row width")
        names = tuple(
            name.strip() for name in raw["target_names"].split("|") if name.strip()
        )
        fields = {
            **raw,
            "uniprot": raw["primaryAccession"],
            "name": names[0] if names else None,
            "synonyms": "|".join(names[1:]),
            "import_profile": "chembl_target_csv_v1",
            "source_path": source_path,
            "source_sha256": digest,
            "source_record": str(record),
        }
        rows.append(
            RawTargetRow(f"stage0:{identity}:{digest}:{record}", fields, target_kind)
        )
    return tuple(rows)


def _classification_row(output: RowResult) -> dict[str, object]:
    """Keep the computed row projection separate from child-table rendering."""
    entry = asdict(output.result)
    raw = output.validated.raw_fields
    legacy_class = (
        raw.get("legacy_iuphar_class")
        or raw.get("old_iuphar_class")
        or raw.get("iuphar_class")
    )
    is_valid = output.validated.input_validation_status == "valid"
    entry.update(
        legacy_iuphar_class=legacy_class,
        legacy_source_status="unverified_historical" if legacy_class else None,
        target_chembl_id=raw.get("target_chembl_id"),
        target_kind=output.validated.target_kind,
        taxon_id=output.validated.taxon,
        uniprot_accessions=output.validated.uniprot_accessions,
        component_ids=sorted(
            {
                item.strip()
                for item in re.split(r"[;|]", raw.get("component_ids") or "")
                if item.strip()
            }
        ),
        name=output.validated.name,
        isoform_id=output.validated.isoform_id,
        isoform_suffix=output.validated.isoform_suffix,
        raw_fields=dict(raw),
        normalized_fields=dict(output.validated.normalized_fields),
        match_method=output.match_methods,
        provider_release=output.provider_release,
        payload_sha256=output.annotation.payload_sha256 if output.annotation else None,
        iuphar_family_ids=output.annotation.family_ids if output.annotation else (),
        iuphar_family_paths=[asdict(path) for path in output.direct.paths]
        if output.direct
        else [],
        local_candidates=output.local.local_candidates if output.local else (),
        ec_categories=output.local.ec_categories if output.local else None,
        multiple_ec_categories=output.local.multiple_ec_categories
        if output.local
        else None,
        ec_numbers=[asdict(number) for number in output.validated.ec_numbers]
        if is_valid
        else None,
        upstream_confidence=_source_confidence(raw) if is_valid else None,
    )
    return entry


def render_batch(result: BatchResult) -> Mapping[str, bytes]:
    """Return deterministic output/evidence/candidates/diagnostics/QC bytes."""
    rows = [_classification_row(output) for output in result.rows]
    return MappingProxyType(
        {
            "classification.json": canonical_json_bytes(rows),
            "evidence.json": canonical_json_bytes(
                [
                    asdict(item)
                    for output in result.rows
                    for item in output.evidence.records
                ]
            ),
            "candidates.json": canonical_json_bytes(
                [asdict(item) for output in result.rows for item in output.candidates]
            ),
            "components.json": canonical_json_bytes(
                [asdict(item) for item in result.components]
            ),
            "diagnostics.json": canonical_json_bytes(
                [
                    {"input_row_id": row, **asdict(diagnostic)}
                    for row, diagnostic in result.diagnostics
                ]
            ),
            "metrics.json": canonical_json_bytes(
                {
                    "status": result.status,
                    **result.metrics,
                }
            ),
        }
    )


def _source_confidence(raw: Mapping[str, str | None]) -> dict[str, str | None] | None:
    keys = ("confidence", "confidence_method", "confidence_version", "confidence_scale")
    return (
        {key: raw.get(key) for key in keys}
        if all(raw.get(key) for key in keys)
        else None
    )


def run_csv_pipeline(
    source: Path,
    *,
    root: Path,
    snapshot: IndexedSnapshot,
    provenance: RunProvenance,
    run_id: str,
) -> tuple[BatchResult, Path | None]:
    """Read the legacy CSV, run the indexed pipeline, publish its bytes once."""
    source_path = _path_inside_root(source, root)
    if not provenance.rules_version:
        raise ValueError("the export needs a named rules version")
    result = classify_batch(
        read_legacy_batch(source_path.read_bytes()),
        snapshot=snapshot,
        provenance=provenance,
        run_id=run_id,
    )
    return result, publish_batch(
        source_path,
        root=root,
        snapshot_id=snapshot.snapshot_id,
        rules_version=provenance.rules_version,
        run_id=run_id,
        result=result,
    )


def publish_batch(
    source: Path,
    *,
    root: Path,
    snapshot_id: str,
    rules_version: str,
    run_id: str,
    result: BatchResult,
) -> Path | None:
    """Publish one immutable result package beside the source, without overwrite."""
    source = _path_inside_root(source, root)
    _, name = result_names(
        source.name,
        snapshot_id=snapshot_id,
        rules_version=rules_version,
        run_id=run_id,
    )
    destination = source.with_name(name + ".targetclass.json")
    if len(destination.name.encode()) > 255:
        raise ValueError("name_too_long")
    artifacts = render_batch(result)
    package = canonical_json_bytes(
        {
            "snapshot_id": snapshot_id,
            "rules_version": rules_version,
            "run_id": run_id,
            "source_name": source.name,
            "artifacts": {
                key: {
                    "sha256": hashlib.sha256(value).hexdigest(),
                    "json": value.decode(),
                }
                for key, value in artifacts.items()
            },
        }
    )
    return destination if _create_new(destination, package, root=root) else None
