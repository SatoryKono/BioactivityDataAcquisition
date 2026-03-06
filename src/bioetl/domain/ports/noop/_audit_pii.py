"""No-op audit and PII hasher implementations."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.ports.audit import AuditEntry, AuditLayer
    from bioetl.domain.types import RunID


class NoOpAudit:
    """No-op implementation of AuditPort."""

    async def log_write(self, _entry: AuditEntry) -> None:
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
        return []

    async def aclose(self) -> None:
        return None


class NoOpPiiHasher:
    """No-op implementation of PiiHasherPort."""

    def hash_value(self, value: str | None) -> str | None:
        return value

    def hash_list(self, values: list[str] | None) -> list[str] | None:
        return values

    def get_salt_id(self) -> str:
        return "noop"
