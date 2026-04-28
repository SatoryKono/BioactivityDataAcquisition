"""Shared field builders for merged Silver write request families."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import TypeVar, TypedDict

from bioetl.domain.types import BronzeRecord

_TRequest = TypeVar("_TRequest")


class _CommonMergedWriteFields(TypedDict):
    """Common keyword payload shared by merged-write request objects."""

    table_name: str
    records: list[BronzeRecord]
    primary_keys: list[str] | None
    completed_at: datetime | None
    run_id: str | None
    sources_used: list[str] | None


def _build_common_merged_write_fields(
    *,
    table_name: str,
    records: list[BronzeRecord],
    primary_keys: list[str] | None = None,
    completed_at: datetime | None = None,
    run_id: str | None = None,
    sources_used: list[str] | None = None,
    ) -> _CommonMergedWriteFields:
    """Build the shared keyword payload for merged write request models."""
    return {
        "table_name": table_name,
        "records": records,
        "primary_keys": primary_keys,
        "completed_at": completed_at,
        "run_id": run_id,
        "sources_used": sources_used,
    }


def _build_merged_write_request(
    request_factory: Callable[..., _TRequest],
    *,
    table_name: str,
    records: list[BronzeRecord],
    primary_keys: list[str] | None = None,
    completed_at: datetime | None = None,
    run_id: str | None = None,
    sources_used: list[str] | None = None,
    **extra_fields: object,
) -> _TRequest:
    """Build one merged-write request object from shared and extra fields."""
    common_fields = _build_common_merged_write_fields(
        table_name=table_name,
        records=records,
        primary_keys=primary_keys,
        completed_at=completed_at,
        run_id=run_id,
        sources_used=sources_used,
    )
    return request_factory(**common_fields, **extra_fields)
