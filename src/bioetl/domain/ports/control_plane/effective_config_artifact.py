"""Port for effective-config artifact inspection."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from bioetl.domain.types import RunID

__all__ = ["EffectiveConfigArtifactStorePort"]


@runtime_checkable
class EffectiveConfigArtifactStorePort(Protocol):
    """Read persisted effective-config artifacts for replay evidence checks."""

    def get(self, artifact_id: str) -> dict[str, object] | None:
        """Load one semantic artifact by identifier."""
        ...

    def get_by_run_id(self, run_id: RunID) -> dict[str, object] | None:
        """Load the semantic artifact linked to one run."""
        ...

    def get_occurrence_by_run_id(self, run_id: RunID) -> dict[str, object] | None:
        """Load the occurrence envelope linked to one run."""
        ...

    def diff_occurrences_by_run_id(
        self,
        left_run_id: RunID,
        right_run_id: RunID,
    ) -> dict[str, object]:
        """Compare semantic and occurrence effective-config evidence."""
        ...
