"""Passive helpers for ``DeltaReader``."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from deltalake import DeltaTable
from deltalake.exceptions import DeltaError

FULL_READ_HEAD_LIMIT = 2147483647
DeltaTableFactory = Callable[[str], DeltaTable]


def count_delta_rows(
    dt: DeltaTable,
    resolved_path: Path,
    *,
    delta_table_factory: DeltaTableFactory,
) -> int:
    """Return row count using metadata when available."""
    native_count = getattr(dt, "count", None)
    if callable(native_count):
        try:
            return int(native_count())
        except (KeyboardInterrupt, SystemExit):
            raise
        except BaseException:
            pass

    dt_fresh = delta_table_factory(str(resolved_path))
    return int(dt_fresh.to_pyarrow_table(columns=[]).num_rows)


def try_native_delta_row_count(dt: DeltaTable) -> int | None:
    """Return ``DeltaTable.count()`` when available without scan fallbacks."""
    native_count = getattr(dt, "count", None)
    if not callable(native_count):
        return None
    try:
        return int(native_count())
    except (KeyboardInterrupt, SystemExit):
        raise
    except (DeltaError, OSError, RuntimeError, TypeError, ValueError):
        return None
