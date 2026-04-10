"""Application service for audit inspection workflows."""

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

    query: dict[str, object]
    entries: tuple[AuditEntry, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe representation for CLI or API responses."""
        return {
            "query": self.query,
            "entries": [entry.to_dict() for entry in self.entries],
        }


@dataclass(slots=True)
class AuditInspectionService:
    """Inspect audit trails through the domain audit port."""

    audit_port: AuditPort

    async def list_entries(
        self,
        *,
        run_id: str | None = None,
        layer: str | AuditLayer | None = None,
        table_name: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> AuditInspectionResult:
        """Return audit entries for the given optional filters."""
        parsed_run_id = self._parse_run_id(run_id)
        resolved_layer = self._resolve_layer(layer)
        entries = await self.audit_port.get_entries(
            run_id=parsed_run_id,
            layer=resolved_layer,
            table_name=table_name,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
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
            entries=tuple(entries),
        )

    async def inspect_run(self, run_id: str, *, limit: int = 100) -> AuditInspectionResult:
        """Return audit entries for one run identifier."""
        return await self.list_entries(run_id=run_id, limit=limit)

    async def inspect_table(
        self,
        table_name: str,
        *,
        layer: str | AuditLayer | None = None,
        limit: int = 100,
    ) -> AuditInspectionResult:
        """Return audit entries for one table, optionally scoped to a layer."""
        return await self.list_entries(table_name=table_name, layer=layer, limit=limit)

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
    def _resolve_layer(layer: str | AuditLayer | None) -> AuditLayer | None:
        """Resolve a string or enum audit layer."""
        if layer is None or isinstance(layer, AuditLayer):
            return layer
        try:
            return AuditLayer(layer.lower())
        except ValueError as exc:
            raise ValueError(f"Invalid audit layer: {layer}") from exc
