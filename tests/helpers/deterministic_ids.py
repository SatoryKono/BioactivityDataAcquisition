"""Deterministic test identity builders for replay-safe fixtures and tests."""

from __future__ import annotations

from uuid import UUID, uuid5

_TEST_ID_NAMESPACE = UUID("6e1d8d7c-7f1a-46f1-94fe-f4d3d8d8d4d1")


def deterministic_uuid(label: str) -> UUID:
    """Return a stable UUID for one logical test identity label."""
    return uuid5(_TEST_ID_NAMESPACE, label)


def deterministic_run_id(label: str) -> str:
    """Return a stable run-id string."""
    return str(deterministic_uuid(f"run:{label}"))


def deterministic_batch_id(label: str) -> str:
    """Return a stable batch-id string."""
    return str(deterministic_uuid(f"batch:{label}"))


def deterministic_table_name(prefix: str, label: str) -> str:
    """Return a stable table name suffix derived from a deterministic UUID."""
    return f"{prefix}_{deterministic_uuid(f'table:{label}').hex[:12]}"
