"""Checkpoint validation evidence builders."""

from __future__ import annotations

from collections.abc import Mapping
from math import isfinite
from typing import cast

from bioetl.application.services.control_plane_evidence import EvidenceCheck
from bioetl.domain.control_plane import RunManifest


def build_checkpoint_checks(
    *,
    manifest: RunManifest | None,
    checkpoint: tuple[object, dict[str, object]] | None,
    aggregate_scope_unknown: bool,
) -> tuple[EvidenceCheck, ...]:
    """Validate one loaded checkpoint without inventing absent integrity data."""
    if aggregate_scope_unknown:
        return (
            EvidenceCheck(
                "scope",
                "UNKNOWN",
                "aggregate_scope_requires_exact_pipeline",
                "Checkpoint validation requires one exact pipeline or run scope.",
            ),
        )
    if checkpoint is None:
        return (
            EvidenceCheck(
                "parse",
                "UNKNOWN",
                "checkpoint_not_found",
                "No persisted checkpoint was found for the requested scope.",
            ),
        )
    checkpoint_run_id, metadata = checkpoint
    checks = [
        EvidenceCheck(
            "parse",
            "OK",
            "checkpoint_parse_ok",
            "The checkpoint adapter parsed the persisted envelope.",
        ),
        _checkpoint_schema_check(metadata),
        _checkpoint_checksum_check(metadata),
    ]
    checks.extend(
        _checkpoint_anchor_checks(
            manifest=manifest,
            checkpoint_run_id=str(checkpoint_run_id),
            metadata=metadata,
        )
    )
    return tuple(checks)


def _checkpoint_schema_check(metadata: Mapping[str, object]) -> EvidenceCheck:
    records_processed = metadata.get("records_processed")
    if records_processed is not None and (
        not isinstance(records_processed, int) or isinstance(records_processed, bool)
    ):
        return EvidenceCheck(
            "schema",
            "ERROR",
            "checkpoint_records_processed_invalid",
            "records_processed must be an integer when present.",
        )
    saved_at = metadata.get("checkpoint_saved_at_epoch_seconds")
    if saved_at is not None:
        if isinstance(saved_at, str | bytes | bytearray | int | float):
            try:
                saved_at_number = float(saved_at)
            except (TypeError, ValueError):
                saved_at_number = float("nan")
        else:
            saved_at_number = float("nan")
        if not isfinite(saved_at_number):
            return EvidenceCheck(
                "schema",
                "ERROR",
                "checkpoint_saved_at_invalid",
                "checkpoint_saved_at_epoch_seconds must be finite when present.",
            )
    return EvidenceCheck(
        "schema",
        "OK",
        "checkpoint_schema_valid",
        "The parsed checkpoint metadata satisfies the supported read schema.",
    )


def _checkpoint_checksum_check(metadata: Mapping[str, object]) -> EvidenceCheck:
    explicit_status = metadata.get("checkpoint_checksum_valid")
    if explicit_status is True:
        return EvidenceCheck(
            "checksum",
            "OK",
            "checkpoint_checksum_verified",
            "Persisted checkpoint evidence records a successful checksum verification.",
        )
    if explicit_status is False:
        return EvidenceCheck(
            "checksum",
            "ERROR",
            "checkpoint_checksum_mismatch",
            "Persisted checkpoint evidence records a checksum mismatch.",
        )
    return EvidenceCheck(
        "checksum",
        "UNKNOWN",
        "checkpoint_checksum_not_recorded",
        "Legacy checkpoint evidence does not record a verifiable checksum result.",
    )


def _checkpoint_anchor_checks(
    *,
    manifest: RunManifest | None,
    checkpoint_run_id: str,
    metadata: Mapping[str, object],
) -> tuple[EvidenceCheck, ...]:
    if manifest is None:
        return (
            EvidenceCheck(
                "anchors",
                "UNKNOWN",
                "manifest_unavailable_for_anchor_validation",
                "A manifest is required to validate checkpoint identity anchors.",
            ),
        )
    expected = {
        "run_id": str(manifest.run_id),
        "manifest_id": manifest.manifest_id,
        "pipeline_name": manifest.pipeline_name,
        "run_type": manifest.run_type.value,
        "execution_fingerprint": manifest.execution_fingerprint,
    }
    actual = {
        "run_id": checkpoint_run_id,
        "manifest_id": _metadata_text(metadata, "manifest_id"),
        "pipeline_name": _metadata_text(metadata, "pipeline_name"),
        "run_type": _metadata_text(metadata, "run_type"),
        "execution_fingerprint": _metadata_text(metadata, "execution_fingerprint"),
    }
    mismatches = sorted(
        name
        for name, expected_value in expected.items()
        if actual[name] is not None and actual[name] != expected_value
    )
    if mismatches:
        return (
            EvidenceCheck(
                "anchors",
                "ERROR",
                "checkpoint_anchor_mismatch",
                "Checkpoint identity anchors differ from the selected manifest: "
                + ", ".join(mismatches),
            ),
        )
    missing = sorted(name for name, value in actual.items() if value is None)
    if missing:
        return (
            EvidenceCheck(
                "anchors",
                "WARNING",
                "checkpoint_anchor_incomplete",
                "Checkpoint identity anchors are absent: " + ", ".join(missing),
            ),
        )
    return (
        EvidenceCheck(
            "anchors",
            "OK",
            "checkpoint_anchors_match_manifest",
            "Checkpoint run, manifest, pipeline, mode, and execution anchors match.",
        ),
    )


def _metadata_text(metadata: Mapping[str, object], key: str) -> str | None:
    value = metadata.get(key)
    run_context = metadata.get("run_context")
    if value is None and isinstance(run_context, Mapping):
        value = cast("Mapping[str, object]", run_context).get(key)
    normalized = str(value or "").strip()
    return normalized or None


__all__ = ["build_checkpoint_checks"]
