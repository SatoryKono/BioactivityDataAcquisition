"""No-op audit and PII hasher implementations."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.ports.audit import AuditEntry, AuditLayer
    from bioetl.domain.types import RunID


class NoOpAudit:
    """No-op implementation of AuditPort."""

    async def log_write(self, _entry: AuditEntry) -> None:
        """No-op implementation of log_write — discards the audit entry.

        Args:
            _entry: Audit entry to log; intentionally ignored by this no-op.
        """
        await asyncio.sleep(0)
        return None

    async def get_entries(
        self,
        run_id: RunID | None = None,  # noqa: ARG002
        layer: AuditLayer | None = None,  # noqa: ARG002
        table_name: str | None = None,  # noqa: ARG002
        start_time: datetime | None = None,  # noqa: ARG002
        end_time: datetime | None = None,  # noqa: ARG002
        limit: int = 100,  # noqa: ARG002
    ) -> list[AuditEntry]:
        """No-op implementation of get_entries — always returns an empty list.

        Args:
            run_id: Optional run identifier filter (ignored).
            layer: Optional Medallion layer filter (ignored).
            table_name: Optional table name filter (ignored).
            start_time: Optional start time filter (ignored).
            end_time: Optional end time filter (ignored).
            limit: Maximum number of entries to return (ignored).

        Returns:
            Empty list.
        """
        del run_id, layer, table_name, start_time, end_time, limit
        await asyncio.sleep(0)
        return []

    async def aclose(self) -> None:
        """No-op implementation of aclose — no resources to release."""
        await asyncio.sleep(0)
        return None

    def log_event(
        self,
        _event_name: str,
        _event_data: dict | None = None,
    ) -> None:
        """No-op implementation of log_event — discards the event.

        Args:
            _event_name: Name of the event to log (ignored).
            _event_data: Event data dictionary (ignored).
        """
        return None


class NoOpPiiHasher:
    """No-op implementation of PiiHasherPort."""

    def hash_value(self, value: str | None) -> str | None:
        """No-op implementation — returns the input value unchanged.

        Args:
            value: PII string to hash.

        Returns:
            The original value without hashing.
        """
        return value

    def hash_list(self, values: list[str] | None) -> list[str] | None:
        """No-op implementation — returns the input list unchanged.

        Args:
            values: List of PII strings to hash.

        Returns:
            The original list without hashing.
        """
        return values

    def get_salt_id(self) -> str:
        """Return the constant 'noop' salt identifier for this implementation."""
        return "noop"
