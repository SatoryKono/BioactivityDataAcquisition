"""Ports for pure classification and application-owned evidence publication."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from bioetl.domain.entities.target_classification_boundary import (
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
    ) -> TargetClassificationResult:
        """Classify one normalized row.

        Args:
            business_data: Normalized business fields.
            input_row_id: Stable source-row identity.
            run_id: Owning pipeline run.
            run_started_at: UTC start timestamp for the run.
        """

    def classify_batch(
        self,
        inputs: tuple[TargetClassificationInput, ...],
        *,
        run_id: str,
        run_started_at: str,
    ) -> TargetClassificationBatch:
        """Classify one immutable batch.

        Args:
            inputs: Normalized rows for this batch.
            run_id: Owning pipeline run.
            run_started_at: UTC start timestamp for the run.
        """


@runtime_checkable
class TargetClassificationEvidencePort(Protocol):
    """Persist evidence without hiding a conflict or an incomplete run."""

    def publish_result(
        self,
        result: TargetClassificationResult,
        *,
        run_id: str,
        batch_id: str,
    ) -> TargetClassificationArtifactReference:
        """Publish one classified row without replacing a conflicting artifact.

        Args:
            result: Classified row to persist.
            run_id: Owning pipeline run.
            batch_id: Source batch that produced the row.
        """

    def finalize_run(
        self, *, run_id: str, expected_row_ids: tuple[str, ...]
    ) -> TargetClassificationArtifactReference:
        """Close the run only when every expected row is present.

        Args:
            run_id: Owning pipeline run.
            expected_row_ids: Row identities the run must have published.
        """


__all__ = ["TargetClassificationEvidencePort", "TargetClassificationPort"]
