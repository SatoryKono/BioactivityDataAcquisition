"""Port for lineage fragment persistence."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from bioetl.domain.lineage import LineageGraphFragment
from bioetl.domain.types import RunID

__all__ = ["LineageStorePort"]


@runtime_checkable
class LineageStorePort(Protocol):
    """Persist and query canonical lineage graph fragments."""

    def save(self, fragment: LineageGraphFragment) -> None:
        """Persist one lineage graph fragment."""
        ...

    def get(self, fragment_id: str) -> LineageGraphFragment | None:
        """Load a lineage fragment by identifier."""
        ...

    def get_occurrence(self, fragment_id: str) -> LineageGraphFragment | None:
        """Load one stored occurrence fragment id without semantic fallback."""
        ...

    def list_by_run_id(self, run_id: RunID) -> list[LineageGraphFragment]:
        """Return fragments linked to one run identifier."""
        ...

    def list_by_manifest_id(self, manifest_id: str) -> list[LineageGraphFragment]:
        """Return fragments linked to one manifest identifier."""
        ...

    def list_by_node_id(self, node_id: str) -> list[LineageGraphFragment]:
        """Return fragments that mention one node identifier."""
        ...
