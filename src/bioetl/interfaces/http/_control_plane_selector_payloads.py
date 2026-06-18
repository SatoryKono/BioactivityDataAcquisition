"""Selector payload rendering helpers for control-plane HTTP selectors."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from bioetl.interfaces.http._control_plane_selector_records import (
    ALL_SCOPE,
    SelectorRecord,
)

RUN_ID_NO_SELECTION = "-"
UNKNOWN_SCOPE = "unknown"
SELECTOR_CONTEXT_CONTRACT = "control_plane_selector_context_v1"


def resolved_via(
    selected: SelectorRecord | None,
    selected_run_id: str | None,
) -> str:
    if selected is None:
        return "no_manifest_for_scope"
    if selected_run_id:
        return "selected_run_id"
    if selected.completed_at_source == "run_ledger_terminal_event":
        return "latest_terminal_run_for_scope"
    return "latest_manifest_created_at_for_scope"


def selected_payload(record: SelectorRecord | None) -> dict[str, object]:
    if record is None:
        return {
            "workflow": ALL_SCOPE,
            "pipeline": UNKNOWN_SCOPE,
            "run_type": ALL_SCOPE,
            "run_id": RUN_ID_NO_SELECTION,
            "run_status": UNKNOWN_SCOPE,
            "provider": UNKNOWN_SCOPE,
            "entity": UNKNOWN_SCOPE,
            "manifest_id": "",
            "completed_at": "",
            "completed_at_source": "none",
            "terminal_event_type": "",
        }
    return {
        "workflow": record.workflow,
        "pipeline": record.pipeline,
        "run_type": record.run_type,
        "run_id": record.run_id,
        "run_status": record.run_status,
        "provider": record.provider,
        "entity": record.entity,
        "manifest_id": record.manifest_id,
        "completed_at": record.completed_at.isoformat(),
        "completed_at_source": record.completed_at_source,
        "terminal_event_type": record.terminal_event_type or "",
    }


def options_payload(records: tuple[SelectorRecord, ...]) -> dict[str, list[str]]:
    return {
        "workflow": _latest_ordered_values(records, lambda record: (record.workflow,)),
        "pipeline": _latest_ordered_values(records, lambda record: (record.pipeline,)),
        "run_type": _latest_ordered_values(records, lambda record: (record.run_type,)),
        "provider": _latest_ordered_values(records, lambda record: (record.provider,)),
        "run_id": _manifest_ordered_values(records, lambda record: record.run_id),
        "run_status": _latest_ordered_values(
            records,
            lambda record: (record.run_status,),
            skip_unknown=False,
        ),
    }


def exact_run_only_fallback_values(fallback_value: str | None) -> list[str]:
    if fallback_value is None:
        return []
    value = fallback_value.strip()
    if not value:
        return []
    return [value]


def _latest_ordered_values(
    records: tuple[SelectorRecord, ...],
    value_factory: Callable[[SelectorRecord], tuple[str, ...]],
    *,
    skip_unknown: bool = True,
) -> list[str]:
    latest_by_value: dict[str, tuple[datetime, str]] = {}
    for record in records:
        values = value_factory(record)
        for value in values:
            if skip_unknown and value == UNKNOWN_SCOPE:
                continue
            current = latest_by_value.get(value)
            candidate = (record.completed_at, record.manifest_id)
            if current is None or candidate > current:
                latest_by_value[value] = candidate
    return [
        value
        for value, _sort_key in sorted(
            latest_by_value.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    ]


def _manifest_ordered_values(
    records: tuple[SelectorRecord, ...],
    value_factory: Callable[[SelectorRecord], str],
) -> list[str]:
    values: list[str] = []
    for record in records:
        value = value_factory(record)
        if value and value not in values:
            values.append(value)
    return values
