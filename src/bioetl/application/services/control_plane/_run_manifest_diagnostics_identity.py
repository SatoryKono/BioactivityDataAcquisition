"""Identity payload helpers for manifest diagnostics."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from bioetl.domain.control_plane import RunManifest
from bioetl.domain.normalization import (
    build_execution_identity_payload,
    compute_execution_identity_fingerprint,
)


def build_canonical_execution_identity(
    *,
    manifest: RunManifest,
    base_summary: Mapping[str, object],
) -> dict[str, object]:
    """Return the canonical execution identity payload for the summary graph."""
    return cast(
        dict[str, object],
        build_execution_identity_payload(
            pipeline_name=manifest.pipeline_name,
            run_type=manifest.run_type.value,
            pipeline_version=cast(str | None, base_summary.get("pipeline_version")),
            git_commit=cast(str | None, base_summary.get("git_commit")),
            dependency_lock_hash=cast(
                str | None, base_summary.get("dependency_lock_hash")
            ),
            effective_config_hash=cast(
                str | None, base_summary.get("effective_config_hash")
            ),
            dq_contract_compatibility_hash=cast(
                str | None, base_summary.get("dq_contract_compatibility_hash")
            ),
            contract_ref=cast(str | None, base_summary.get("contract_ref")),
            contract_version=cast(str | None, base_summary.get("contract_version")),
            effective_config_artifact_id=cast(
                str | None, base_summary.get("effective_config_artifact_id")
            ),
            exact_replay=cast(bool | None, base_summary.get("requested_exact_replay")),
            input_snapshot_fingerprint=cast(
                str | None, base_summary.get("input_snapshot_identity_fingerprint")
            ),
            silver_filter_compatibility_mode=str(
                manifest.runtime_config.get(
                    "silver_filter_compatibility_mode",
                    "structural_only_auto_promote",
                )
            ),
        ),
    )


def build_degraded_runtime_anchor_payload(
    *,
    manifest: RunManifest,
    base_summary: Mapping[str, object],
) -> dict[str, object]:
    """Return the degraded runtime anchor payload used for fallback identity."""
    return {
        key: value
        for key, value in {
            "manifest_id": manifest.manifest_id,
            "effective_config_hash": base_summary.get("effective_config_hash"),
            "contract_ref": base_summary.get("contract_ref"),
            "contract_version": base_summary.get("contract_version"),
            "effective_config_artifact_id": base_summary.get(
                "effective_config_artifact_id"
            ),
        }.items()
        if value is not None
    }


def build_degraded_runtime_anchor(payload: dict[str, object]) -> dict[str, object]:
    """Return the legacy fallback identity anchor wrapper."""
    return {
        "compatibility_scope": "legacy_fallback_only",
        "fingerprint": (
            compute_execution_identity_fingerprint(payload) if payload else None
        ),
        "payload": payload,
    }


__all__ = [
    "build_canonical_execution_identity",
    "build_degraded_runtime_anchor",
    "build_degraded_runtime_anchor_payload",
]
