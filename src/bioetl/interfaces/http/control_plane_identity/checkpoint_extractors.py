"""Checkpoint extraction helpers for Control Plane identity.

Legacy HTTP contract compatibility layer - sunset date: 2026-12-31
This module extracts legacy HTTP identity anchor values.
"""

from __future__ import annotations

from typing import cast

from bioetl.domain.control_plane import RunManifest
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata
from bioetl.interfaces.http.control_plane_identity.formatting import (
    is_present,
    mapping_value,
)
from bioetl.interfaces.http.control_plane_identity.types import AnchorValues


def checkpoint_anchor_payload(manifest: RunManifest) -> dict[str, object]:
    for payload in (
        manifest.runtime_config,
        manifest.resolved_config,
        manifest.launch_context,
    ):
        checkpoint = mapping_value(
            payload,
            "checkpoint_metadata",
            "persisted_checkpoint_metadata",
            "checkpoint_anchors",
            "persisted_checkpoint_anchors",
        )
        if checkpoint:
            return normalize_checkpoint_metadata_payload(checkpoint)
    reproducibility = mapping_value(
        manifest.resolved_config,
        "reproducibility_diagnostics",
        "reproducibility",
    )
    if reproducibility:
        checkpoint = mapping_value(reproducibility, "checkpoint_anchors")
        if checkpoint:
            persisted = mapping_value(
                checkpoint,
                "checkpoint",
                "checkpoint_metadata",
                "persisted_checkpoint_anchors",
            )
            return normalize_checkpoint_metadata_payload(persisted or checkpoint)
    return {}


def normalize_checkpoint_metadata_payload(
    checkpoint: object,
) -> dict[str, object]:
    """Normalize persisted CheckpointMetadata-like mappings into anchor payloads."""
    if not isinstance(checkpoint, dict):
        return {}
    normalized = CheckpointMetadata.from_dict(
        {str(key): value for key, value in checkpoint.items()}
    ).to_dict()
    # Preserve custom metadata keys that are not modeled on CheckpointMetadata yet.
    for key, value in checkpoint.items():
        normalized.setdefault(str(key), value)
    return cast("dict[str, object]", normalized)


def checkpoint_value(manifest: RunManifest, *keys: str) -> object | None:
    checkpoint = checkpoint_anchor_payload(manifest)
    for key in keys:
        value = checkpoint.get(key)
        if is_present(value):
            return value
    return first_payload_value(manifest, *keys)


def composite_run_identity(manifest: RunManifest) -> object | None:
    return checkpoint_value(manifest, "composite_run_identity")


def first_payload_value(manifest: RunManifest, *keys: str) -> object | None:
    for payload in (
        manifest.runtime_config,
        manifest.launch_context,
        manifest.resolved_config,
    ):
        for key in keys:
            value = payload.get(key)
            if is_present(value):
                return value
    return None


def extract_checkpoint_anchors(
    checkpoint_data: dict[str, object],
) -> list[AnchorValues]:
    """Extract legacy HTTP identity anchor values from checkpoint mappings."""
    from bioetl.interfaces.http.control_plane_identity.anchor_values import (
        anchor_values_from_mapping,
    )

    payload = dict(checkpoint_data)
    checkpoint_id = payload.get("checkpoint_id")
    if checkpoint_id is not None:
        payload.setdefault("checkpoint_file_id", checkpoint_id)
    return anchor_values_from_mapping(
        payload,
        source="checkpoint",
        anchor_names=(
            "run_id",
            "manifest_id",
            "checkpoint_file_id",
            "execution_fingerprint",
        ),
    )


__all__ = [
    "checkpoint_anchor_payload",
    "checkpoint_value",
    "composite_run_identity",
    "extract_checkpoint_anchors",
    "first_payload_value",
    "normalize_checkpoint_metadata_payload",
]
