"""Role-aware immutable Stage-0 admission; the historical V1 writer is unchanged."""

from __future__ import annotations

import csv
import io
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, cast

from .io import canonical_json_bytes, sha256_bytes
from .models import ProvenanceClaim

MaterialRole = Literal["cohort", "evidence"]


@dataclass(frozen=True, slots=True)
class Stage0MaterialV2:
    """An explicitly selected role and format, never inferred from a filename."""

    source_path: str
    source_sha256: str
    role: MaterialRole
    format_version: str
    target_kind: str | None = None
    conversion_ledger_source: str | None = None

    def __post_init__(self) -> None:
        _required_text(self.source_path)
        _required_text(self.format_version)
        _require_sha256(self.source_sha256)
        if self.role not in {"cohort", "evidence"}:
            raise ValueError("unknown Stage-0 material role")
        if self.role == "cohort" and (
            self.target_kind != "protein" or not self.conversion_ledger_source
        ):
            raise ValueError("cohort needs an explicit protein import and conversion ledger")


@dataclass(frozen=True, slots=True)
class Stage0V2Request:
    cohort_id: str
    approval_reference: str
    environment: str
    materials: tuple[Stage0MaterialV2, ...]
    provenance_claims: tuple[ProvenanceClaim, ...] = ()


@dataclass(frozen=True, slots=True)
class VerifiedStage0V2:
    """All frozen bytes verified; only cohort copies are executable inputs."""

    document: Mapping[str, object]
    cohort_payloads: Mapping[str, bytes]
    evidence_payloads: Mapping[str, bytes]
    cohort_digests: tuple[tuple[str, str], ...]
    evidence_digests: tuple[tuple[str, str], ...]
    conversion_ledger_digests: tuple[tuple[str, str], ...]
    cohort_manifest_sha256: str
    conversion_ledger_sha256: str


def _required_text(value: object) -> str:
    if not isinstance(value, str) or not value.strip() or "[...]" in value:
        raise ValueError("explicit non-placeholder Stage-0 text required")
    return value


def _require_sha256(value: object) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("expected lowercase SHA-256")
    return value


def _inside(root: Path, relative: object) -> Path:
    value = _required_text(relative)
    if Path(value).is_absolute():
        raise ValueError("Stage-0 paths must be relative")
    result = (root / value).resolve()
    if not result.is_relative_to(root.resolve()) or result == root.resolve():
        raise ValueError("Stage-0 artifact escapes its root")
    return result


def _object(payload: bytes) -> dict[str, object]:
    value = json.loads(payload)
    if not isinstance(value, dict):
        raise ValueError("expected a Stage-0 JSON object")
    return cast("dict[str, object]", value)


def _checked(payload: bytes, digest: object, byte_count: object) -> None:
    if type(byte_count) is not int or len(payload) != byte_count:
        raise ValueError("Stage-0 source byte count differs from manifest")
    if sha256_bytes(payload) != _require_sha256(digest):
        raise ValueError("Stage-0 source bytes differ from manifest")


def _request_materials(request: Stage0V2Request) -> dict[str, Stage0MaterialV2]:
    for value in (request.cohort_id, request.approval_reference, request.environment):
        _required_text(value)
    indexed = {item.source_path: item for item in request.materials}
    if len(indexed) != len(request.materials) or not any(
        item.role == "cohort" for item in request.materials
    ):
        raise ValueError("Stage-0 needs distinct materials and at least one cohort")
    return indexed


def _provenance_bindings(
    claims: Sequence[ProvenanceClaim], materials: Mapping[str, Stage0MaterialV2]
) -> list[dict[str, object]]:
    bindings: list[dict[str, object]] = []
    for claim in claims:
        if claim.source_ref not in materials:
            raise ValueError("provenance must bind a copied cohort or evidence material")
        source = materials[claim.source_ref]
        if claim.source_sha256 != source.source_sha256:
            raise ValueError("provenance source digest differs from copied material")
        for value in (claim.field_id, claim.rule_or_process, claim.confirmation_owner):
            _required_text(value)
        bindings.append({**asdict(claim), "source_role": source.role})
    return bindings


def publish_stage0_v2(
    request: Stage0V2Request, *, repo_root: Path, output_dir: Path
) -> Path:
    """Publish a new occurrence, preserving all source and historical V1 bytes."""
    root, output = repo_root.resolve(), output_dir.resolve()
    if not output.is_relative_to(root) or output == root:
        raise ValueError("Stage-0 output must be a new directory inside the workspace")
    materials = _request_materials(request)
    bindings = _provenance_bindings(request.provenance_claims, materials)
    payloads = {name: _inside(root, name).read_bytes() for name in materials}
    for name, item in materials.items():
        if sha256_bytes(payloads[name]) != item.source_sha256:
            raise ValueError("Stage-0 source digest mismatch before copy")
    output.mkdir(parents=True, exist_ok=False)
    copies = _publish_copies(output, materials, payloads)
    artifacts = {
        "content_checks.json": canonical_json_bytes(copies),
        "provenance_map.json": canonical_json_bytes(bindings),
        "stage_report.json": canonical_json_bytes({
            "stage_status": "recorded_without_biological_acceptance",
            "biological_accuracy_accepted": False,
        }),
        "cohort_manifest.json": canonical_json_bytes({
            "artifact": "bioetl_target_cohort", "schema_version": 1,
            "cohort_id": request.cohort_id,
            "sources": [asdict(item) for item in request.materials if item.role == "cohort"],
        }),
        "conversion_ledgers.json": canonical_json_bytes({
            item.source_path: materials[item.conversion_ledger_source or ""].source_sha256
            for item in request.materials if item.role == "cohort"
        }),
    }
    for name, raw in artifacts.items():
        (output / name).write_bytes(raw)
    manifest = {
        "artifact": "stage0_manifest", "schema_version": 2, "stage": "0",
        "cohort_id": request.cohort_id, "approval_reference": request.approval_reference,
        "environment": request.environment, "copies": copies,
        "provenance_bindings": bindings, "biological_accuracy_accepted": False,
        "artifact_sha256": {name: sha256_bytes(raw) for name, raw in artifacts.items()},
    }
    path = output / "manifest.json"
    path.write_bytes(canonical_json_bytes(manifest))
    verify_stage0_v2(path, sha256_bytes(path.read_bytes()), tuple(
        name for name, item in materials.items() if item.role == "cohort"
    ))
    return path


def _publish_copies(
    output: Path, materials: Mapping[str, Stage0MaterialV2], payloads: Mapping[str, bytes]
) -> list[dict[str, object]]:
    (output / "copies").mkdir()
    copies: list[dict[str, object]] = []
    for index, (name, material) in enumerate(sorted(materials.items())):
        relative = f"copies/{index:04d}-{material.source_sha256}.bin"
        (output / relative).write_bytes(payloads[name])
        copies.append({**asdict(material), "sha256": material.source_sha256,
                       "copy_path": relative, "byte_count": len(payloads[name])})
    return copies


def verify_stage0_v2(
    path: Path, expected_sha256: str, selected_cohort_sources: tuple[str, ...]
) -> VerifiedStage0V2:
    """Verify every copy and ledger before selecting the complete cohort set."""
    raw = path.read_bytes()
    if sha256_bytes(raw) != _require_sha256(expected_sha256):
        raise ValueError("expected pinned Stage-0 manifest")
    document = _object(raw)
    if (document.get("artifact"), document.get("schema_version"), document.get("stage")) != (
        "stage0_manifest", 2, "0"
    ):
        raise ValueError("not a Stage-0 V2 manifest")
    entries, payloads = _verified_materials(path.parent, document)
    cohorts = {name: raw for name, raw in payloads.items() if entries[name].role == "cohort"}
    if not cohorts or set(selected_cohort_sources) != set(cohorts):
        raise ValueError("volume requires the complete pinned Stage-0 cohort source set")
    if len(selected_cohort_sources) != len(set(selected_cohort_sources)):
        raise ValueError("duplicate Stage-0 cohort selection")
    evidence = {name: raw for name, raw in payloads.items() if entries[name].role == "evidence"}
    ledgers = _verify_conversion_ledgers(entries, payloads)
    artifacts = cast("dict[str, str]", document["artifact_sha256"])
    return VerifiedStage0V2(document, cohorts, evidence,
        tuple((name, sha256_bytes(raw)) for name, raw in sorted(cohorts.items())),
        tuple((name, sha256_bytes(raw)) for name, raw in sorted(evidence.items())), ledgers,
        artifacts["cohort_manifest.json"], artifacts["conversion_ledgers.json"])


def _verified_materials(
    root: Path, document: Mapping[str, object]
) -> tuple[dict[str, Stage0MaterialV2], dict[str, bytes]]:
    artifacts = cast("dict[str, str]", document["artifact_sha256"])
    if not {"content_checks.json", "provenance_map.json", "stage_report.json",
            "cohort_manifest.json", "conversion_ledgers.json"}.issubset(artifacts):
        raise ValueError("missing Stage-0 V2 proof artifacts")
    for name, digest in artifacts.items():
        if sha256_bytes(_inside(root, name).read_bytes()) != _require_sha256(digest):
            raise ValueError("Stage-0 proof hash mismatch")
    entries: dict[str, Stage0MaterialV2] = {}
    payloads: dict[str, bytes] = {}
    for item in cast("list[dict[str, object]]", document["copies"]):
        material = _material_from_mapping(item)
        if material.source_path in entries:
            raise ValueError("duplicate Stage-0 material identity")
        raw = _inside(root, item["copy_path"]).read_bytes()
        _checked(raw, item["sha256"], item["byte_count"])
        if item["sha256"] != material.source_sha256:
            raise ValueError("Stage-0 source and copy digest differ")
        entries[material.source_path], payloads[material.source_path] = material, raw
    _verify_provenance(document, entries)
    return entries, payloads


def _material_from_mapping(item: Mapping[str, object]) -> Stage0MaterialV2:
    return Stage0MaterialV2(
        _required_text(item["source_path"]), _require_sha256(item["source_sha256"]),
        cast("MaterialRole", item["role"]), _required_text(item["format_version"]),
        cast("str | None", item["target_kind"]),
        cast("str | None", item["conversion_ledger_source"]),
    )


def _verify_provenance(
    document: Mapping[str, object], entries: Mapping[str, Stage0MaterialV2]
) -> None:
    for claim in cast("list[dict[str, object]]", document.get("provenance_bindings", [])):
        bound = ProvenanceClaim(
            _required_text(claim["field_id"]), _required_text(claim["source_ref"]),
            _require_sha256(claim["source_sha256"]), _required_text(claim["rule_or_process"]),
            _required_text(claim["confirmation_owner"]),
        )
        result = _provenance_bindings((bound,), entries)
        if result[0] != claim:
            raise ValueError("Stage-0 provenance binding differs from copied source role")


def _verify_conversion_ledgers(
    entries: Mapping[str, Stage0MaterialV2], payloads: Mapping[str, bytes]
) -> tuple[tuple[str, str], ...]:
    result: list[tuple[str, str]] = []
    for name, entry in entries.items():
        if entry.role != "cohort":
            continue
        ledger_name = entry.conversion_ledger_source or ""
        if ledger_name not in entries or entries[ledger_name].role != "evidence":
            raise ValueError("cohort conversion ledger must be copied evidence")
        ledger = _object(payloads[ledger_name])
        if (ledger.get("artifact"), ledger.get("schema_version")) != ("bioetl_target_cohort_conversion", 1):
            raise ValueError("unsupported cohort conversion ledger")
        canonical = cast("dict[str, object]", ledger["canonical"])
        if canonical.get("format_version") != entry.format_version:
            raise ValueError("conversion ledger canonical format differs from cohort")
        _checked(payloads[name], canonical["sha256"], canonical["byte_count"])
        raw = cast("dict[str, object]", ledger["raw_source"])
        matching = [key for key, material in entries.items()
                    if material.role == "evidence" and material.source_sha256 == raw["sha256"]]
        if not matching:
            raise ValueError("conversion ledger has no copied raw-source evidence")
        _checked(payloads[matching[0]], raw["sha256"], raw["byte_count"])
        _verify_conversion_rows(payloads[name], ledger)
        result.append((name, sha256_bytes(payloads[ledger_name])))
    return tuple(sorted(result))


def _verify_conversion_rows(canonical: bytes, ledger: Mapping[str, object]) -> None:
    """Verify every canonical record binding rather than accepting a summary hash."""
    if ledger.get("source_schema_version") != "chembl.target.normalized_silver.v1":
        raise ValueError("conversion requires the normalized ChEMBL target v1 schema")
    _required_text(ledger.get("technical_mapping_reference"))
    _required_text(ledger.get("environment"))
    rows = list(csv.DictReader(io.StringIO(canonical.decode("utf-8"), newline="")))
    records = cast("list[dict[str, object]]", ledger["records"])
    metadata = cast("dict[str, object]", ledger["canonical"])
    if not rows or len(rows) != len(records) or metadata.get("row_count") != len(rows):
        raise ValueError("conversion row count differs from the frozen canonical cohort")
    for index, (row, record) in enumerate(zip(rows, records, strict=True), 1):
        expected = {"source_record": index, "canonical_row_id": row["input_row_id"],
                    "canonical_row_sha256": sha256_bytes(canonical_json_bytes(row))}
        if record != expected:
            raise ValueError("conversion ledger row binding mismatch")


__all__ = ["Stage0MaterialV2", "Stage0V2Request", "VerifiedStage0V2",
           "publish_stage0_v2", "verify_stage0_v2"]
