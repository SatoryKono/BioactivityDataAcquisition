"""Run-scoped classification with separate pure and evidence-publication phases."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports.target_classification import (
        TargetClassificationEvidencePort,
        TargetClassificationPort,
    )
    from bioetl.domain.target_classification import (
        TargetClassificationArtifactReference,
        TargetClassificationResult,
    )


@dataclass(slots=True)
class TargetClassificationSession:
    """Keep filesystem effects out of transformer classification callbacks."""

    classifier: TargetClassificationPort
    evidence: TargetClassificationEvidencePort
    mode: Literal["shadow", "enrich"]
    _pending: dict[tuple[str, str, int], TargetClassificationResult] = field(
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
        row_id = f"chembl.target:{target_id}:{key[1]}:{index}"
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

    def publish(self, context: PipelineContext, index: int) -> None:
        """Publish from the application finalizer, after successful row finalization."""
        key = self._key(context, index)
        result = self._pending.pop(key, None)
        if result is None:
            return
        self.evidence.publish_result(result, run_id=key[0], batch_id=key[1])
        self._published.setdefault(key[0], set()).add(result.input_row_id)

    def finalize(self, context: PipelineContext) -> TargetClassificationArtifactReference:
        """Complete evidence only after the runner has completed all data writes."""
        run_id = str(context.run_id)
        expected = tuple(sorted(self._published.get(run_id, set())))
        return self.evidence.finalize_run(run_id=run_id, expected_row_ids=expected)


__all__ = ["TargetClassificationSession"]
