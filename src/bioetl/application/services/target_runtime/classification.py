"""Run-scoped classification with separate pure and evidence-publication phases."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from bioetl.application.services.run_reports.observations import record_run_observation
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.entities.target_classification_boundary import (
        TargetClassificationArtifactReference,
        TargetClassificationResult,
    )
    from bioetl.domain.ports import (
        TargetClassificationEvidencePort,
        TargetClassificationPort,
    )


@dataclass(slots=True)
class TargetClassificationRunState:
    """Keep filesystem effects out of transformer classification callbacks."""

    classifier: TargetClassificationPort
    evidence: TargetClassificationEvidencePort
    mode: Literal["shadow", "enrich"]
    normalization_version: str
    rules_version: str
    classification_schema_version: str
    matching_policy_version: str
    _pending: dict[tuple[str, str, int], TargetClassificationResult] = field(
        default_factory=dict, init=False
    )
    _detached: dict[tuple[str, str, str], TargetClassificationResult] = field(
        default_factory=dict, init=False
    )
    _published: dict[str, set[str]] = field(default_factory=dict, init=False)

    @staticmethod
    def _key(context: PipelineContext, index: int) -> tuple[str, str, int]:
        return (str(context.run_id), str(context.source_batch_id or "direct"), index)

    def enrich(
        self, context: PipelineContext, index: int, business_data: JsonDict
    ) -> JsonDict:
        """Classify in memory; shadow leaves the original business projection intact."""
        key = self._key(context, index)
        target_id = business_data.get("target_id")
        row_id = f"chembl.target:{target_id}"
        anchor = context.replay_timestamp_anchor or context.started_at
        result = self.classifier.classify_record(
            business_data,
            input_row_id=row_id,
            run_id=key[0],
            run_started_at=anchor.isoformat(),
        )
        self._pending[key] = result
        if self.mode == "shadow":
            return business_data
        return {**business_data, **result.projection}

    def classify_detached(
        self,
        *,
        run_id: str,
        batch_id: str,
        row_id: str,
        business_data: JsonDict,
        run_started_at: str,
    ) -> TargetClassificationResult:
        """Classify one enriched row and keep evidence unpublished."""
        result = self.classifier.classify_record(
            business_data,
            input_row_id=row_id,
            run_id=run_id,
            run_started_at=run_started_at,
        )
        self._detached[(run_id, batch_id, row_id)] = result
        return result

    def commit_detached(self, run_id: str) -> TargetClassificationArtifactReference:
        """Publish every detached row for ``run_id``, then complete the run."""
        pending = sorted(key for key in self._detached if key[0] == run_id)
        for key in pending:
            result = self._detached.pop(key)
            self.evidence.publish_result(result, run_id=key[0], batch_id=key[1])
            self._published.setdefault(key[0], set()).add(result.input_row_id)
        return self.finalize_run_id(run_id)

    def abandon_detached(self, run_id: str) -> None:
        """Drop unpublished detached rows. A completed manifest is not written."""
        pending = [key for key in self._detached if key[0] == run_id]
        for key in pending:
            self._detached.pop(key, None)

    def discard(self, context: PipelineContext, index: int) -> None:
        """Release unpublished evidence when row finalization ends."""
        self._pending.pop(self._key(context, index), None)

    def publish(self, context: PipelineContext, index: int) -> None:
        """Publish from the application finalizer, after successful row finalization."""
        key = self._key(context, index)
        result = self._pending.pop(key, None)
        if result is None:
            return
        self.evidence.publish_result(result, run_id=key[0], batch_id=key[1])
        self._published.setdefault(key[0], set()).add(result.input_row_id)

    def finalize(
        self, context: PipelineContext
    ) -> TargetClassificationArtifactReference:
        """Complete evidence only after the runner has completed all data writes."""
        return self.finalize_run_id(str(context.run_id))

    def finalize_run_id(self, run_id: str) -> TargetClassificationArtifactReference:
        """Complete one run occurrence after its rows have been published."""
        expected = tuple(sorted(self._published.get(run_id, set())))
        reference = self.evidence.finalize_run(run_id=run_id, expected_row_ids=expected)
        record_run_observation(
            "Target Classification",
            verdict="OK",
            reason="verified_target_classification_evidence",
            facts={
                "run_id": run_id,
                "mode": self.mode,
                "snapshot_manifest_sha256": self.classifier.snapshot_manifest_sha256,
                "profile_sha256": self.classifier.profile_sha256,
                "normalization_version": self.normalization_version,
                "rules_version": self.rules_version,
                "classification_schema_version": self.classification_schema_version,
                "matching_policy_version": self.matching_policy_version,
                "row_count": len(expected),
                "evidence_manifest_uri": reference.uri,
                "evidence_manifest_sha256": reference.sha256,
            },
        )
        return reference


__all__ = ["TargetClassificationRunState"]
