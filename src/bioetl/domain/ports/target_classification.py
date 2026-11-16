"""Ports for pure classification and application-owned evidence publication."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from bioetl.domain.target_classification import (
    TargetClassificationArtifactReference,
    TargetClassificationBatch,
    TargetClassificationInput,
    TargetClassificationResult,
)


@runtime_checkable
class TargetClassificationPort(Protocol):
    """Classify normalized rows using an already loaded immutable snapshot."""

    profile_sha256: str
    snapshot_id: str
    snapshot_manifest_sha256: str
    immutable_uri: str

    def classify_record(
        self,
        business_data: Mapping[str, object],
        *,
        input_row_id: str,
        run_id: str,
        run_started_at: str,
    ) -> TargetClassificationResult: ...

    def classify_batch(
        self,
        inputs: tuple[TargetClassificationInput, ...],
        *,
        run_id: str,
        run_started_at: str,
    ) -> TargetClassificationBatch: ...


@runtime_checkable
class TargetClassificationEvidencePort(Protocol):
    """Persist evidence without hiding a conflict or an incomplete run."""

    def publish_result(
        self,
        result: TargetClassificationResult,
        *,
        run_id: str,
        batch_id: str,
    ) -> TargetClassificationArtifactReference: ...

    def finalize_run(
        self, *, run_id: str, expected_row_ids: tuple[str, ...]
    ) -> TargetClassificationArtifactReference: ...


__all__ = ["TargetClassificationEvidencePort", "TargetClassificationPort"]
