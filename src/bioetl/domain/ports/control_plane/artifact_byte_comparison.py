"""Port contract for byte-level artifact comparison in forensic diff flows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol

__all__ = ["ArtifactByteComparisonPort"]


class ArtifactByteComparisonPort(Protocol):
    """Compare artifact references for byte-level forensic equivalence."""

    def compare_artifacts(
        self,
        left_refs: Sequence[Mapping[str, object]],
        right_refs: Sequence[Mapping[str, object]],
    ) -> dict[str, object]:
        """Return deterministic byte-comparison verdict for two artifact sets."""
        ...
