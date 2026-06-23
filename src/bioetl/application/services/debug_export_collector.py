"""Collector for debug export audit rows."""

from __future__ import annotations

from .debug_export_collector_gold_mixin import DebugExportGoldRowsMixin
from .debug_export_collector_helpers import (
    build_dq_summary_rows,
    get_sorted_lineage_rows,
)
from .debug_export_collector_transform_mixin import DebugExportTransformRowsMixin


class DebugExportCollector(DebugExportTransformRowsMixin, DebugExportGoldRowsMixin):
    """Collect and store audit rows for debug export."""

    def __init__(
        self,
        *,
        run_id: str,
        pipeline_id: str,
        provider_id: str,
        workflow_id: str,
        manifest_id: str | None = None,
    ) -> None:
        self._run_id = run_id
        self._pipeline_id = pipeline_id
        self._provider_id = provider_id
        self._workflow_id = workflow_id
        self._manifest_id = manifest_id
        self._bronze_rows: list[dict[str, object]] = []
        self._silver_full_rows: list[dict[str, object]] = []
        self._silver_rejected_rows: list[dict[str, object]] = []
        self._silver_quarantine_rows: list[dict[str, object]] = []
        self._gold_full_rows: list[dict[str, object]] = []
        self._gold_rejected_rows: list[dict[str, object]] = []
        self._lineage_rows: list[dict[str, object]] = []
        self._gold_record_index_by_hash: dict[str, int] = {}

    def attach_manifest_id(self, manifest_id: str | None) -> None:
        """Attach a manifest id to the collector for final pack assembly."""
        self._manifest_id = manifest_id


__all__ = [
    "DebugExportCollector",
    "build_dq_summary_rows",
    "get_sorted_lineage_rows",
]
