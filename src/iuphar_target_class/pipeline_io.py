"""Import and render the target-class batch without rewriting source data."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from pathlib import Path
from types import MappingProxyType

from .comparison import (
    ParityInputs,
    ParityPublication,
    build_m_parity_report,
    write_m_parity_report,
)
from .csv_io import read_csv_records
from .delivery import _create_new, _path_inside_root, result_names
from .models import RawTargetRow, RunProvenance
from .pipeline import BatchResult, IndexedSnapshot, RowResult, classify_batch
from .stage0.io import canonical_json_bytes

BIOETL_TARGET_KERNEL_CSV_V1 = "bioetl_target_kernel_csv_v1"
_INVALID_CSV_ROW_WIDTH = "invalid CSV row width"
_BIOETL_KERNEL_COLUMNS = frozenset(
    {
        "input_row_id",
        "target_kind",
        "target_chembl_id",
        "target_id",
        "uniprot",
        "organism",
        "name",
    }
)
_IMPORT_PROVENANCE_COLUMNS = frozenset(
    {"import_profile", "source_path", "source_sha256", "source_record"}
)


def read_bioetl_target_kernel_csv_v1(
    content: bytes, *, source_path: str, target_kind: str
) -> tuple[RawTargetRow, ...]:
    """Read explicit kernel fields with canonical TaxID text, without guessing.

    This profile keeps ChEMBL and provider identity separate. Species names,
    padded TaxIDs and unknown sentinels must be converted by a source-owned
    producer before this boundary; blank taxonomy remains explicitly missing.
    """
    if not source_path.strip() or target_kind not in {"protein", "complex"}:
        raise ValueError(
            "canonical CSV import requires a source and explicit target kind"
        )
    headers, source_rows = read_csv_records(content)
    _require_bioetl_kernel_header(headers)
    digest = hashlib.sha256(content).hexdigest()
    rows = tuple(
        _bioetl_kernel_row(raw, record, source_path, target_kind, digest)
        for record, raw in enumerate(source_rows, 1)
    )
    if len({row.input_row_id for row in rows}) != len(rows):
        raise ValueError("duplicate canonical CSV input_row_id")
    return rows


def _require_bioetl_kernel_header(headers: Sequence[str]) -> None:
    if (
        len(headers) != len(set(headers))
        or not _BIOETL_KERNEL_COLUMNS.issubset(headers)
        or bool(_IMPORT_PROVENANCE_COLUMNS.intersection(headers))
        or any(not header.strip() for header in headers)
    ):
        raise ValueError("invalid bioetl_target_kernel_csv_v1 header")


def _bioetl_kernel_identity(raw: dict[str, str], target_kind: str) -> str:
    """Require a coherent row before constructing its source provenance."""
    if None in raw or any(value is None for value in raw.values()):
        raise ValueError(_INVALID_CSV_ROW_WIDTH)
    identity = raw["input_row_id"]
    if not identity.strip() or any(mark in identity for mark in ("/", "\n", "\r")):
        raise ValueError("invalid canonical CSV input_row_id")
    if raw["target_kind"] != target_kind:
        raise ValueError("canonical CSV target_kind differs from selected profile")
    return identity


def _require_canonical_taxon(taxon: str) -> None:
    if taxon and re.fullmatch(r"[1-9]\d*", taxon, flags=re.ASCII) is None:
        raise ValueError(
            "canonical CSV organism must be a positive ASCII TaxID or blank"
        )


def _bioetl_kernel_row(
    raw: dict[str, str],
    record: int,
    source_path: str,
    target_kind: str,
    digest: str,
) -> RawTargetRow:
    identity = _bioetl_kernel_identity(raw, target_kind)
    _require_canonical_taxon(raw["organism"])
    fields: dict[str, str | None] = {
        key: value
        for key, value in raw.items()
        if key not in {"input_row_id", "target_kind"}
    }
    fields.update(
        import_profile=BIOETL_TARGET_KERNEL_CSV_V1,
        source_path=source_path,
        source_sha256=digest,
        source_record=str(record),
    )
    return RawTargetRow(identity, fields, target_kind)


def read_legacy_batch(content: bytes) -> tuple[RawTargetRow, ...]:
    """Decode a CSV, retaining original legacy class only as a source field."""
    headers, source_rows = read_csv_records(content)
    if len(headers) != len(set(headers)) or not {
        "input_row_id",
        "target_kind",
    }.issubset(headers):
        raise ValueError("invalid CSV header: expected unique columns and row ID/kind")
    rows: list[RawTargetRow] = []
    for row in source_rows:
        if None in row or any(value is None for value in row.values()):
            raise ValueError(_INVALID_CSV_ROW_WIDTH)
        fields: dict[str, str | None] = {
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
    headers, source_rows = read_csv_records(content)
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
    if headers != expected:
        raise ValueError("invalid chembl_target_csv_v1 header")
    digest = hashlib.sha256(content).hexdigest()
    identity = hashlib.sha256(source_path.encode("utf-8")).hexdigest()
    rows = [
        _chembl_target_row(raw, record, source_path, target_kind, digest, identity)
        for record, raw in enumerate(source_rows, 1)
    ]
    return tuple(rows)


def _chembl_target_row(
    raw: dict[str, str],
    record: int,
    source_path: str,
    target_kind: str,
    digest: str,
    identity: str,
) -> RawTargetRow:
    """Preserve source columns and record identity after strict width checks."""
    if None in raw or any(value is None for value in raw.values()):
        raise ValueError(_INVALID_CSV_ROW_WIDTH)
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
    return RawTargetRow(f"stage0:{identity}:{digest}:{record}", fields, target_kind)


def _component_id_projection(raw: Mapping[str, str | None]) -> list[str]:
    return sorted(
        {
            item.strip()
            for item in re.split(r"[;|]", raw.get("component_ids") or "")
            if item.strip()
        }
    )


def _classification_context_fields(
    output: RowResult, is_valid: bool
) -> dict[str, object]:
    """Keep local inference and valid-only input projections in source order."""
    return {
        "local_candidates": output.local.local_candidates if output.local else (),
        "ec_categories": output.local.ec_categories if output.local else None,
        "multiple_ec_categories": output.local.multiple_ec_categories
        if output.local
        else None,
        "ec_numbers": [asdict(number) for number in output.validated.ec_numbers]
        if is_valid
        else None,
        "upstream_confidence": _source_confidence(output.validated.raw_fields)
        if is_valid
        else None,
    }


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
        component_ids=_component_id_projection(raw),
        name=output.validated.name,
        isoform_id=output.validated.isoform_id,
        isoform_suffix=output.validated.isoform_suffix,
        raw_fields=dict(raw),
        normalized_fields=dict(output.validated.normalized_fields),
        match_method=output.match_methods,
        provider_release=output.provider_release,
        payload_sha256=output.annotation.payload_sha256 if output.annotation else None,
        iuphar_family_ids=output.annotation.family_ids if output.annotation else (),
        iuphar_subclasses=list(output.direct.iuphar_subclasses)
        if output.direct
        else [],
        iuphar_annotation_capability=(
            output.direct.annotation_capability if output.direct else None
        ),
        iuphar_family_paths=[asdict(path) for path in output.direct.paths]
        if output.direct
        else [],
        **_classification_context_fields(output, is_valid),
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
    parity: ParityPublication | None = None,
) -> tuple[BatchResult, Path | None]:
    """Read the legacy CSV, run the indexed pipeline, publish its bytes once.

    ``parity`` is optional. When it is present the seal and historical rows
    were fixed before this call, and the M parity report is written beside the
    source. It is not a member of the proof package.
    """
    source_path = _path_inside_root(source, root)
    if not provenance.rules_version:
        raise ValueError("the export needs a named rules version")
    result = classify_batch(
        read_legacy_batch(source_path.read_bytes()),
        snapshot=snapshot,
        provenance=provenance,
        run_id=run_id,
    )
    published = publish_batch(
        source_path,
        root=root,
        snapshot_id=snapshot.snapshot_id,
        rules_version=provenance.rules_version,
        run_id=run_id,
        result=result,
    )
    if parity is not None:
        publish_m_parity(result, parity, directory=source_path.parent, root=root)
    return result, published


def publish_m_parity(
    result: BatchResult,
    publication: ParityPublication,
    *,
    directory: Path,
    root: Path,
) -> Path:
    """Write ``m-parity-report.json`` from a sealed request and this batch."""
    report = build_m_parity_report(
        ParityInputs(
            original_m=publication.original_m,
            new_result=parity_rows_from_batch(result),
            saved_excel=publication.saved_excel,
            independent_reference=publication.independent_reference,
            control_run=publication.control_run,
            basis_seal=publication.basis_seal,
        )
    )
    return write_m_parity_report(report, _path_inside_root(directory, root))


def parity_rows_from_batch(result: BatchResult) -> tuple[dict[str, str], ...]:
    """Project classified rows onto the string fields the parity report compares."""
    return tuple(_parity_row(_classification_row(output)) for output in result.rows)


_PARITY_SCALAR_FIELDS = (
    "capability",
    "decision_status",
    "effective_class",
    "effective_source",
    "gene_id",
    "gene_symbol",
    "input_row_id",
    "input_validation_status",
    "isoform_id",
    "isoform_suffix",
    "iuphar_annotation_status",
    "iuphar_class",
    "iuphar_mapping_rule_id",
    "iuphar_mapping_version",
    "iuphar_subclass",
    "iuphar_type_raw",
    "legacy_iuphar_class",
    "local_class",
    "local_status",
    "match_status",
    "matched_target_id",
    "normalization_version",
    "organism",
    "rules_version",
    "schema_version",
    "snapshot_id",
    "target_id",
    "target_kind",
    "uniprot",
)
_PARITY_SEQUENCE_FIELDS = (
    "candidate_target_ids",
    "conflict_codes",
    "effective_subclasses",
    "family_ids",
    "iuphar_class_candidates",
    "iuphar_family_ids",
    "iuphar_family_paths",
    "input_errors",
    "local_candidates",
    "local_rule_ids",
    "local_subclasses",
)
_PARITY_IDENTITY_FROM_RAW = (
    "gene_id",
    "gene_symbol",
    "organism",
    "target_id",
    "uniprot",
)
_PARITY_VERSION_FIELDS = (
    "normalization_version",
    "rules_version",
    "schema_version",
)


def _parity_row(entry: Mapping[str, object]) -> dict[str, str]:
    flat = _parity_flat(entry)
    row: dict[str, str] = {}
    for field in _PARITY_SCALAR_FIELDS:
        text = _parity_scalar(flat.get(field))
        if text is not None:
            row[field] = text
    for field in _PARITY_SEQUENCE_FIELDS:
        text = _parity_sequence(flat.get(field))
        if text is not None:
            row[field] = text
    provenance = flat.get("provenance")
    if isinstance(provenance, str):
        row["provenance"] = provenance
    return row


def _parity_flat(entry: Mapping[str, object]) -> dict[str, object]:
    flat = dict(entry)
    raw = entry.get("raw_fields")
    if isinstance(raw, Mapping):
        for key in _PARITY_IDENTITY_FROM_RAW:
            if flat.get(key) is None:
                flat[key] = raw.get(key)
    provenance = entry.get("provenance")
    if isinstance(provenance, Mapping):
        for key in _PARITY_VERSION_FIELDS:
            if flat.get(key) is None:
                flat[key] = provenance.get(key)
        flat["provenance"] = _parity_json(dict(provenance))
    return flat


def _parity_scalar(value: object) -> str | None:
    if isinstance(value, str):
        return value
    return None


def _parity_sequence(value: object) -> str | None:
    if not isinstance(value, list | tuple):
        return None
    return _parity_json(list(value))


def _parity_json(value: object) -> str:
    return json.dumps(
        _json_ready(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _json_ready(value: object) -> object:
    if isinstance(value, list | tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    return value


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
