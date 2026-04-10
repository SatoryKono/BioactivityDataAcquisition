"""Application service for inspecting persisted audit entries."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from bioetl.domain.ports import AuditEntry, AuditLayer, AuditPort
from bioetl.domain.types import RunID

__all__ = [
    "AuditInspectionResult",
    "AuditInspectionService",
]


@dataclass(frozen=True, slots=True)
class AuditInspectionResult:
    """Operator-facing audit query result."""

    query: dict[str, object] = field(default_factory=dict)
    entries: tuple[AuditEntry, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe representation."""
        return {
            "query": self.query,
            "entries": [entry.to_dict() for entry in self.entries],
        }


@dataclass(slots=True)
class AuditInspectionService:
    """Read-only audit inspection service."""

    audit_port: AuditPort

    async def list_entries(
        self,
        *,
        run_id: str | None = None,
        layer: AuditLayer | str | None = None,
        table_name: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> AuditInspectionResult:
        """Query audit entries using operator-facing filters."""
        resolved_run_id = self._parse_run_id(run_id) if run_id is not None else None
        resolved_layer = self._resolve_layer(layer)
        entries = tuple(
            await self.audit_port.get_entries(
                run_id=resolved_run_id,
                layer=resolved_layer,
                table_name=table_name,
                start_time=start_time,
                end_time=end_time,
                limit=limit,
            )
        )
        return AuditInspectionResult(
            query={
                "run_id": run_id,
                "layer": resolved_layer.value if resolved_layer is not None else None,
                "table_name": table_name,
                "start_time": start_time.isoformat() if start_time else None,
                "end_time": end_time.isoformat() if end_time else None,
                "limit": limit,
            },
            entries=entries,
        )

    async def inspect_run(
        self,
        run_id: str,
        *,
        limit: int = 100,
    ) -> AuditInspectionResult:
        """Return the recent audit trail for one pipeline run."""
        return await self.list_entries(run_id=run_id, limit=limit)

    async def inspect_table(
        self,
        table_name: str,
        *,
        layer: AuditLayer | str | None = None,
        limit: int = 100,
    ) -> AuditInspectionResult:
        """Return recent audit entries for one table/path target."""
        return await self.list_entries(
            layer=layer,
            table_name=table_name,
            limit=limit,
        )

    async def aclose(self) -> None:
        """Close the underlying audit port."""
        await self.audit_port.aclose()

    @staticmethod
    def _parse_run_id(run_id: str | None) -> RunID | None:
        """Parse a UUID string into a RunID when provided."""
        if run_id is None:
            return None
        try:
            return RunID(UUID(run_id))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid run_id: {run_id}") from exc

    @staticmethod
    def _resolve_layer(layer: AuditLayer | str | None) -> AuditLayer | None:
        """Parse optional layer filters from strings into AuditLayer values."""
        if layer is None or isinstance(layer, AuditLayer):
            return layer
        try:
            return AuditLayer(layer.lower())
        except ValueError as exc:
            raise ValueError(f"Invalid audit layer: {layer}") from exc
