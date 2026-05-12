"""Historical replay support helpers for run-manifest CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

from bioetl.application.services.control_plane.historical_replay_certification_service import (
    HistoricalReplaySnapshotCertification,
)
from bioetl.application.services.control_plane.historical_replay_closure_service import (
    HistoricalReplayResidualDisposition,
)
from bioetl.application.services.control_plane.historical_replay_corpus_service import (
    HistoricalReplayBulkCertificationSpec,
)

__all__ = [
    "_coerce_bulk_certification_specs",
    "_load_residual_dispositions",
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
    dispositions: list[HistoricalReplayResidualDisposition] = []
    for item in raw_dispositions:
        if not isinstance(item, dict):
            raise ValueError("Residual disposition entries must be JSON objects")
        manifest_id = str(item.get("manifest_id") or "").strip()
        disposition = str(item.get("disposition") or "").strip()
        rationale = str(item.get("rationale") or "").strip()
        if not manifest_id or not disposition or not rationale:
            raise ValueError(
                "Residual disposition entries require manifest_id, disposition, and rationale"
            )
        evidence_refs = item.get("evidence_refs")
        if evidence_refs is None:
            evidence_ref_values: tuple[str, ...] = ()
        elif isinstance(evidence_refs, list):
            evidence_ref_values = tuple(
                str(value).strip() for value in evidence_refs if str(value).strip()
            )
        else:
            raise ValueError("Residual disposition evidence_refs must be a list")
        dispositions.append(
            HistoricalReplayResidualDisposition(
                manifest_id=manifest_id,
                disposition=disposition,
                rationale=rationale,
                evidence_refs=evidence_ref_values,
            )
        )
    return tuple(dispositions)
