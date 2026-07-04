"""Read-side mixin for file-backed lineage fragment persistence."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter

from bioetl.domain.lineage import LineageGraphFragment
from bioetl.domain.types import RunID
from bioetl.infrastructure.control_plane._read_metrics import (
    emit_control_plane_read_metrics,
)


class FileLineageQueriesMixin:
    """Query methods for ``FileLineageStore``."""

    base_path: Path
    metrics: object | None

    def get_occurrence(self, fragment_id: str) -> LineageGraphFragment | None:
        """Load one stored occurrence fragment id without semantic fallback."""
        started_at = perf_counter()
        status = "success"
        try:
            fragment = self._load_fragment(fragment_id)
            if fragment is None:
                status = "miss"
            return fragment
        except (OSError, TypeError, ValueError):
            status = "failed"
            raise
        finally:
            self._emit_read_observation(
                operation="get_occurrence",
                status=status,
                started_at=started_at,
            )

    def get(self, fragment_id: str) -> LineageGraphFragment | None:
        """Load one fragment by identifier if present."""
        started_at = perf_counter()
        status = "success"
        try:
            fragment = self._load_fragment(fragment_id)
            if fragment is None:
                stored_fragment_ids = self._load_fragment_ids(
                    self._semantic_fragment_index_path(fragment_id),
                    key=fragment_id,
                )
                if not stored_fragment_ids:
                    status = "miss"
                    return None
                if len(stored_fragment_ids) > 1:
                    status = "failed"
                    raise ValueError(
                        "Semantic lineage fragment id resolves to multiple stored "
                        "occurrence records; use run_id or manifest_id lookup for "
                        "historical reconstruction"
                    )
                fragment = self._load_fragment(stored_fragment_ids[0])
                if fragment is None:
                    status = "miss"
                    return None
            return fragment
        except (OSError, TypeError, ValueError):
            status = "failed"
            raise
        finally:
            self._emit_read_observation(
                operation="get",
                status=status,
                started_at=started_at,
            )

    def list_by_run_id(self, run_id: RunID) -> list[LineageGraphFragment]:
        """Return fragments linked to one run identifier."""
        return self._list_from_index(
            self._run_index_path(str(run_id)),
            key=str(run_id),
            operation="list_by_run_id",
        )

    def list_by_manifest_id(self, manifest_id: str) -> list[LineageGraphFragment]:
        """Return fragments linked to one manifest identifier."""
        return self._list_from_index(
            self._manifest_index_path(manifest_id),
            key=manifest_id,
            operation="list_by_manifest_id",
        )

    def list_by_node_id(self, node_id: str) -> list[LineageGraphFragment]:
        """Return fragments that mention one node identifier."""
        return self._list_from_index(
            self._node_index_path(node_id),
            key=node_id,
            operation="list_by_node_id",
        )

    def _list_from_index(
        self,
        index_path: Path,
        *,
        key: str,
        operation: str,
    ) -> list[LineageGraphFragment]:
        started_at = perf_counter()
        status = "success"
        try:
            fragments = self._load_from_index(index_path, key=key)
            if not fragments:
                status = "miss"
            return fragments
        except (OSError, TypeError, ValueError):
            status = "failed"
            raise
        finally:
            self._emit_read_observation(
                operation=operation,
                status=status,
                started_at=started_at,
            )

    def _emit_read_observation(
        self,
        *,
        operation: str,
        status: str,
        started_at: float,
    ) -> None:
        emit_control_plane_read_metrics(
            self.metrics,
            store="lineage",
            operation=operation,
            status=status,
            duration_seconds=perf_counter() - started_at,
        )
