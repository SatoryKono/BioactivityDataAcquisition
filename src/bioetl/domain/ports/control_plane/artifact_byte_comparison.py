"""Port contract for semantic-first artifact comparison in forensic diff flows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol, runtime_checkable

__all__ = ["ArtifactByteComparisonPort"]


@runtime_checkable
class ArtifactByteComparisonPort(Protocol):
    """Compare artifact references semantically while preserving raw-byte evidence."""

    def compare_artifacts(
        self,
        left_refs: Sequence[Mapping[str, object]],
        right_refs: Sequence[Mapping[str, object]],
    ) -> dict[str, object]:
        """Return deterministic semantic and raw-byte comparison verdicts."""
        ...
