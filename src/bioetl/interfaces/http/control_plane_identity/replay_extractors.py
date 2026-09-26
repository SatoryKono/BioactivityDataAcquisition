"""Replay and runtime-state extraction helpers for Control Plane identity."""

from __future__ import annotations

from bioetl.domain.control_plane import RunInputSnapshotRef, RunLedgerEntry, RunManifest
from bioetl.interfaces.http.control_plane_identity.checkpoint_extractors import (
    composite_run_identity,
    first_payload_value,
)
from bioetl.interfaces.http.control_plane_identity.formatting import is_present
from bioetl.interfaces.http.control_plane_identity.manifest_extractors import (
    input_snapshot_fingerprint,
)
from bioetl.interfaces.http.control_plane_identity.spec_constants import (
    TERMINAL_STATUSES,
)


def exact_replay_blockers(
    manifest: RunManifest,
    snapshots: tuple[RunInputSnapshotRef, ...],
    diagnostics: dict[str, object],
    *,
    snapshot_fingerprint: object | None,
) -> list[str]:
    """Return missing exact-replay anchors, or a pre-reported blocker list.

    Prefers ``diagnostics['exact_replay_blockers']`` when present. Otherwise,
    when the run requested exact replay, lists required identity fields that
    are absent from the manifest or snapshot set.
    """
    reported = diagnostics.get("exact_replay_blockers")
    if isinstance(reported, list | tuple | set):
        return [str(item) for item in reported if is_present(item)]
    if not requested_exact_replay(manifest):
        return []
    blockers: list[str] = []
    code = manifest.code_provenance
    required = {
        "execution_fingerprint": manifest.execution_fingerprint,
        "effective_config_hash": code.effective_config_hash,
        "effective_config_artifact_id": code.effective_config_artifact_id,
        "input_snapshot_identity_fingerprint": snapshot_fingerprint,
        "input_snapshot_ids": [item.snapshot_id for item in snapshots],
        "replay_of_run_id": manifest.replay_of_run_id,
    }
    for name, value in required.items():
        if not is_present(value):
            blockers.append(name)
    return blockers


def runtime_mode(manifest: RunManifest) -> str:
    """Render run_type plus active runtime flags for identity evidence."""
    flags = [
        f"{name}={value}"
        for name in (
            "execution_context",
            "resume",
            "dry_run",
            "exact_replay",
            "use_cached_bronze",
        )
        if (value := first_payload_value(manifest, name))
        not in (None, False, "", [], {})
    ]
    return " | ".join([manifest.run_type.value, *flags])


def replay_mode(manifest: RunManifest) -> str:
    """Classify the run as exact_replay, replay, or the native run_type."""
    if requested_exact_replay(manifest):
        return "exact_replay"
    if manifest.replay_of_run_id or manifest.replay_of_manifest_id:
        return "replay"
    return manifest.run_type.value


def exact_replay_eligible(
    manifest: RunManifest,
    snapshots: tuple[RunInputSnapshotRef, ...],
) -> bool:
    """Return True when required exact-replay identity anchors are present."""
    code = manifest.code_provenance
    required = (
        manifest.execution_fingerprint,
        code.effective_config_hash,
        code.effective_config_artifact_id,
        input_snapshot_fingerprint(snapshots),
    )
    return all(is_present(item) for item in required)


def requested_exact_replay(manifest: RunManifest) -> bool:
    """Return True when the manifest payload requested exact replay."""
    value = first_payload_value(manifest, "exact_replay", "requested_exact_replay")
    return value is True or str(value).strip().lower() == "true"


def is_replay(manifest: RunManifest) -> bool:
    """Return True when the run is a replay or requested exact replay."""
    return bool(manifest.replay_of_run_id or manifest.replay_of_manifest_id) or (
        requested_exact_replay(manifest)
    )


def is_composite(manifest: RunManifest) -> bool:
    """Return True when the run is a composite pipeline or composite identity."""
    return manifest.pipeline_name.startswith("composite_") or (
        manifest.provider == "composite" or bool(composite_run_identity(manifest))
    )


def is_terminal(ledger_entries: tuple[RunLedgerEntry, ...]) -> bool:
    """Return True when any ledger entry is in a terminal status."""
    return any(
        str(entry.status or "").lower() in TERMINAL_STATUSES for entry in ledger_entries
    )


__all__ = [
    "exact_replay_blockers",
    "exact_replay_eligible",
    "is_composite",
    "is_replay",
    "is_terminal",
    "replay_mode",
    "requested_exact_replay",
    "runtime_mode",
]
