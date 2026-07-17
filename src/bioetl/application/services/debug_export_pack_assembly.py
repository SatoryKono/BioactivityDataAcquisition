"""Debug export pack assembly helpers."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.domain.types import DebugExportPack

from .debug_export_collector import build_dq_summary_rows, get_sorted_lineage_rows
from .debug_reason_dictionary import DEBUG_REASON_DICTIONARY

if TYPE_CHECKING:
    from .debug_export_collector import DebugExportCollector


def build_debug_export_pack(
    *,
    collector: DebugExportCollector,
    run_id: str,
    pipeline_id: str,
    provider_id: str,
    workflow_id: str,
    output_root: str,
    formats: tuple[str, ...],
    include_bom: bool,
    max_rows_per_sheet: int,
    created_at_factory: Callable[[], datetime],
    status: str,
) -> DebugExportPack:
    """Build the in-memory audit pack from collected rows."""
    silver_rejected_rows = collector._silver_rejected_rows
    silver_quarantine_rows = collector._silver_quarantine_rows
    gold_rejected_rows = collector._gold_rejected_rows
    tables = {
        "bronze_index": tuple(collector._bronze_rows),
        "silver_full": tuple(collector._silver_full_rows),
        "silver_rejected": tuple(silver_rejected_rows),
        "silver_quarantine": tuple(silver_quarantine_rows),
        "gold_full": tuple(collector._gold_full_rows),
        "gold_rejected": tuple(gold_rejected_rows),
        "dq_summary": build_dq_summary_rows(
            run_id=run_id,
            workflow_id=workflow_id,
            pipeline_id=pipeline_id,
            silver_rejected_rows=silver_rejected_rows,
            silver_quarantine_rows=silver_quarantine_rows,
            gold_rejected_rows=gold_rejected_rows,
        ),
        "lineage": get_sorted_lineage_rows(collector._lineage_rows),
        "reason_dictionary": DEBUG_REASON_DICTIONARY,
    }
    return DebugExportPack(
        run_id=run_id,
        pipeline_id=pipeline_id,
        provider_id=provider_id,
        workflow_id=workflow_id,
        manifest_id=collector._manifest_id,
        status=status,
        output_root=output_root,
        formats=formats,
        include_bom=include_bom,
        max_rows_per_sheet=max_rows_per_sheet,
        created_at=created_at_factory(),
        tables=tables,
        reason_dictionary=DEBUG_REASON_DICTIONARY,
    )


__all__ = ["build_debug_export_pack"]
