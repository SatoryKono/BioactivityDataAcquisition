from __future__ import annotations

# Shared immutable identity fields for control-plane input snapshots.
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InputSnapshotIdentity:
    """Provider and artifact anchors that identify one Bronze input snapshot."""

    provider: str
    entity: str
    pipeline_name: str
    snapshot_id: str
    content_hash: str
    immutable_uri: str
    bronze_batch_ref: str
