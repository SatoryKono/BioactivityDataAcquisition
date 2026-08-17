"""Historical replay support helpers for run-manifest CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

from bioetl.application.services.control_plane.replay.historical_certification_service import (
    HistoricalReplaySnapshotCertification,
)
from bioetl.application.services.control_plane.replay.historical_closure_service import (
    HistoricalReplayResidualDisposition,
)
from bioetl.application.services.control_plane.replay.historical_corpus_service import (
    HistoricalReplayBulkCertificationSpec,
)
from bioetl.application.services.control_plane.replay.historical_universe_service import (
    HistoricalReplayUniverseExternalRecord,
)

__all__ = [
    "_coerce_bulk_certification_specs",
    "_load_residual_dispositions",
    "_load_universe_external_records",
]


def _coerce_bulk_certification_specs(
    payload: object,
) -> tuple[HistoricalReplayBulkCertificationSpec, ...]:
    if not isinstance(payload, dict):
        raise ValueError("Bulk certification plan must be a JSON object")
    raw_specs = payload.get("specs")
    if not isinstance(raw_specs, list) or not raw_specs:
        raise ValueError("Bulk certification plan requires a non-empty specs list")
    specs: list[HistoricalReplayBulkCertificationSpec] = []
    for item in raw_specs:
        if not isinstance(item, dict):
            raise ValueError("Bulk certification specs must be JSON objects")
        manifest_id = str(item.get("manifest_id") or "").strip()
        if not manifest_id:
            raise ValueError("Bulk certification spec is missing manifest_id")
        raw_certifications = item.get("certifications")
        if not isinstance(raw_certifications, list) or not raw_certifications:
            raise ValueError(
                f"Bulk certification spec {manifest_id!r} requires certifications"
            )
        specs.append(
            HistoricalReplayBulkCertificationSpec(
                manifest_id=manifest_id,
                certifications=tuple(
                    _coerce_snapshot_certification(manifest_id, certification)
                    for certification in raw_certifications
                ),
            )
        )
    return tuple(specs)


def _coerce_snapshot_certification(
    manifest_id: str,
    payload: object,
) -> HistoricalReplaySnapshotCertification:
    if not isinstance(payload, dict):
        raise ValueError(
            f"Bulk certification entries for {manifest_id!r} must be JSON objects"
        )
    required_fields = (
        "provider",
        "entity",
        "pipeline_name",
        "snapshot_id",
        "content_hash",
        "immutable_uri",
        "bronze_batch_ref",
    )
    missing = [
        field for field in required_fields if not str(payload.get(field) or "").strip()
    ]
    if missing:
        raise ValueError(
            f"Bulk certification entry for {manifest_id!r} is missing fields: "
            + ", ".join(missing)
        )
    return HistoricalReplaySnapshotCertification(
        provider=str(payload["provider"]).strip(),
        entity=str(payload["entity"]).strip(),
        pipeline_name=str(payload["pipeline_name"]).strip(),
        snapshot_id=str(payload["snapshot_id"]).strip(),
        content_hash=str(payload["content_hash"]).strip(),
        immutable_uri=str(payload["immutable_uri"]).strip(),
        bronze_batch_ref=str(payload["bronze_batch_ref"]).strip(),
        query=_optional_text(payload.get("query")),
        query_fingerprint=_optional_text(payload.get("query_fingerprint")),
        certification_artifact_ref=_optional_text(
            payload.get("certification_artifact_ref")
        ),
        certification_basis=_optional_text(payload.get("certification_basis"))
        or "retained_bronze_artifact",
        upstream_run_id=_optional_text(payload.get("upstream_run_id")),
        upstream_manifest_id=_optional_text(payload.get("upstream_manifest_id")),
    )


def _optional_text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _coerce_evidence_refs(evidence_refs: object) -> tuple[str, ...]:
    if evidence_refs is None:
        return ()
    if not isinstance(evidence_refs, list):
        raise ValueError("Residual disposition evidence_refs must be a list")
    return tuple(str(value).strip() for value in evidence_refs if str(value).strip())


def _coerce_residual_disposition(
    item: object,
) -> HistoricalReplayResidualDisposition:
    if not isinstance(item, dict):
        raise ValueError("Residual disposition entries must be JSON objects")
    manifest_id = str(item.get("manifest_id") or "").strip()
    disposition = str(item.get("disposition") or "").strip()
    rationale = str(item.get("rationale") or "").strip()
    if not manifest_id or not disposition or not rationale:
        raise ValueError(
            "Residual disposition entries require manifest_id, disposition, and rationale"
        )
    return HistoricalReplayResidualDisposition(
        manifest_id=manifest_id,
        disposition=disposition,
        rationale=rationale,
        evidence_refs=_coerce_evidence_refs(item.get("evidence_refs")),
    )


def _load_residual_dispositions(
    dispositions_path: Path | None,
) -> tuple[HistoricalReplayResidualDisposition, ...]:
    if dispositions_path is None:
        return ()
    payload = json.loads(dispositions_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Residual disposition file must be a JSON object")
    raw_dispositions = payload.get("dispositions")
    if not isinstance(raw_dispositions, list):
        raise ValueError("Residual disposition file requires a dispositions list")
    return tuple(_coerce_residual_disposition(item) for item in raw_dispositions)


def _load_universe_external_records(
    pack_paths: tuple[Path, ...],
) -> tuple[HistoricalReplayUniverseExternalRecord, ...]:
    """Load authoritative archived/offline historical-run packs for universe reports."""
    records: list[HistoricalReplayUniverseExternalRecord] = []
    for pack_path in pack_paths:
        payload = json.loads(pack_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Universe pack must be a JSON object")
        pack_ref = str(payload.get("pack_id") or pack_path.name).strip()
        raw_records = payload.get("records")
        if not isinstance(raw_records, list) or not raw_records:
            raise ValueError(
                f"Universe pack {pack_path} requires a non-empty records list"
            )
        for item in raw_records:
            records.append(_coerce_universe_external_record(item, pack_ref=pack_ref))
    return tuple(records)


def _require_json_bool(value: object, *, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be a JSON boolean")
    return value


def _coerce_universe_external_record(
    payload: object,
    *,
    pack_ref: str,
) -> HistoricalReplayUniverseExternalRecord:
    if not isinstance(payload, dict):
        raise ValueError("Universe pack entries must be JSON objects")
    required_fields = (
        "manifest_id",
        "run_id",
        "pipeline_name",
        "provider",
        "entity",
        "execution_context",
        "certification_status",
        "replay_occurrence_kind",
    )
    missing = [
        field for field in required_fields if not str(payload.get(field) or "").strip()
    ]
    if missing:
        raise ValueError(
            "Universe pack entry is missing fields: " + ", ".join(sorted(missing))
        )
    blocking_reasons = payload.get("blocking_reasons", [])
    if not isinstance(blocking_reasons, list):
        raise ValueError("Universe pack blocking_reasons must be a list")
    return HistoricalReplayUniverseExternalRecord(
        manifest_id=str(payload["manifest_id"]).strip(),
        run_id=str(payload["run_id"]).strip(),
        pipeline_name=str(payload["pipeline_name"]).strip(),
        provider=str(payload["provider"]).strip(),
        entity=str(payload["entity"]).strip(),
        execution_context=str(payload["execution_context"]).strip(),
        certification_status=str(payload["certification_status"]).strip(),
        replay_occurrence_kind=str(payload["replay_occurrence_kind"]).strip(),
        blocking_reasons=tuple(
            str(value).strip() for value in blocking_reasons if str(value).strip()
        ),
        evidence_residency=str(payload.get("evidence_residency") or "archived").strip(),
        durable_evidence_coverage=_require_json_bool(
            payload.get("durable_evidence_coverage", False),
            field_name="durable_evidence_coverage",
        ),
        source_pack_ref=pack_ref,
    )
