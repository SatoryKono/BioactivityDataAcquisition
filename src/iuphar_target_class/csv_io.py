"""Bounded in-memory CSV parsing with reversible process-global limits."""

from __future__ import annotations

import csv
import io
from threading import RLock
from typing import cast

_FIELD_LIMIT_LOCK = RLock()


def read_csv_records(
    content: bytes, *, strict: bool = True
) -> tuple[tuple[str, ...], tuple[dict[str, str], ...]]:
    """Read all verified bytes before restoring the caller's CSV field limit.

    A field cannot exceed the byte length of its complete input. Cooperating
    readers serialize the temporary limit change; errors restore it as well.
    Width validation remains with each versioned importer.
    """
    with _FIELD_LIMIT_LOCK:
        previous = csv.field_size_limit()
        try:
            csv.field_size_limit(max(previous, len(content)))
            reader = csv.DictReader(
                io.StringIO(content.decode("utf-8-sig"), newline=""), strict=strict
            )
            headers = tuple(reader.fieldnames or ())
            rows = tuple(reader)
            return headers, cast("tuple[dict[str, str], ...]", rows)
        finally:
            csv.field_size_limit(previous)
