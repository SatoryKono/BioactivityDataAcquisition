"""Deterministic test identity builders for replay-safe fixtures and tests."""

from __future__ import annotations

import inspect
import os
from collections import defaultdict
from uuid import UUID, uuid5

_TEST_ID_NAMESPACE = UUID("6e1d8d7c-7f1a-46f1-94fe-f4d3d8d8d4d1")
_CALLSITE_ORDINALS: defaultdict[tuple[str, str, int], int] = defaultdict(int)


def deterministic_uuid(label: str) -> UUID:
    """Return a stable UUID for one logical test identity label."""
    return uuid5(_TEST_ID_NAMESPACE, label)


def deterministic_uuid_from_callsite(namespace: str) -> UUID:
    """Return a stable UUID for replay-sensitive tests without hand-written labels."""
    frame = inspect.currentframe()
    caller = frame.f_back if frame is not None else None
    if caller is None:
        return deterministic_uuid(f"{namespace}:unknown")

    current_test = os.environ.get("PYTEST_CURRENT_TEST", "module").split(" ", 1)[0]
    key = (current_test, caller.f_code.co_name, caller.f_lineno)
    ordinal = _CALLSITE_ORDINALS[key]
    _CALLSITE_ORDINALS[key] += 1
    return deterministic_uuid(
        f"{namespace}:{current_test}:{caller.f_code.co_name}:{caller.f_lineno}:{ordinal}"
    )


def deterministic_run_id(label: str) -> str:
    """Return a stable run-id string."""
    return str(deterministic_uuid(f"run:{label}"))


def deterministic_batch_id(label: str) -> str:
    """Return a stable batch-id string."""
    return str(deterministic_uuid(f"batch:{label}"))


def deterministic_table_name(prefix: str, label: str) -> str:
    """Return a stable table name suffix derived from a deterministic UUID."""
    return f"{prefix}_{deterministic_uuid(f'table:{label}').hex[:12]}"
