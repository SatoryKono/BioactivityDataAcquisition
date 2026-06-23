"""Shared types for Control Plane identity evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from bioetl.domain.control_plane import RunLedgerEntry

IDENTITY_EVIDENCE_CONTRACT = "control_plane_identity_evidence_v1"


class LedgerEntryProvider(Protocol):
    """Minimal ledger surface required by identity evidence assembly."""

    def list_entries(self, manifest_id: str) -> list[RunLedgerEntry]: ...


@dataclass(frozen=True, slots=True, init=False)
class AnchorSpec:
    """Static presentation and policy metadata for one identity anchor."""

    priority: str
    name: str
    label: str
    source: str
    value_format: str
    why: str
    rendering: str
    copy: bool
    drilldown: str
    missing_severity: str

    def __init__(
        self,
        priority: str,
        name: str | None = None,
        label: str | None = None,
        source: str | None = None,
        value_format: str | None = None,
        why: str | None = None,
        rendering: str | None = None,
        copy: bool | None = None,
        drilldown: str | None = None,
        missing_severity: str | None = None,
        *,
        anchor_name: str | None = None,
        display_name: str | None = None,
        source_location: str | None = None,
        data_type: str | None = None,
        description: str | None = None,
        display_mode: str | None = None,
        is_identifier: bool | None = None,
        usage_locations: str | None = None,
        implementation_status: str | None = None,
    ) -> None:
        """Initialize canonical specs while accepting legacy HTTP contract names."""
        resolved_missing_severity = missing_severity or implementation_status
        if resolved_missing_severity == "SHIPPED":
            resolved_missing_severity = "INFO"
        values = {
            "priority": priority,
            "name": name or anchor_name,
            "label": label or display_name,
            "source": source or source_location,
            "value_format": value_format or data_type,
            "why": why or description,
            "rendering": rendering or display_mode,
            "copy": copy if copy is not None else is_identifier,
            "drilldown": drilldown or usage_locations,
            "missing_severity": resolved_missing_severity,
        }
        missing = [key for key, value in values.items() if value is None]
        if missing:
            fields = ", ".join(missing)
            raise TypeError(f"missing required AnchorSpec fields: {fields}")
        for field_name, value in values.items():
            object.__setattr__(self, field_name, value)

    @property
    def anchor_name(self) -> str:
        """Backward-compatible alias for ``name``."""
        return self.name

    @property
    def display_name(self) -> str:
        """Backward-compatible alias for ``label``."""
        return self.label

    @property
    def source_location(self) -> str:
        """Backward-compatible alias for ``source``."""
        return self.source

    @property
    def data_type(self) -> str:
        """Backward-compatible alias for ``value_format``."""
        return self.value_format

    @property
    def description(self) -> str:
        """Backward-compatible alias for ``why``."""
        return self.why

    @property
    def display_mode(self) -> str:
        """Backward-compatible alias for ``rendering``."""
        return self.rendering

    @property
    def is_identifier(self) -> bool:
        """Backward-compatible alias for ``copy``."""
        return self.copy

    @property
    def usage_locations(self) -> str:
        """Backward-compatible alias for ``drilldown``."""
        return self.drilldown

    @property
    def implementation_status(self) -> str:
        """Legacy implementation-status view derived from severity metadata."""
        if self.missing_severity == "INFO":
            return "SHIPPED"
        if self.missing_severity == "WARNING":
            return "DEGRADED"
        return self.missing_severity


@dataclass(frozen=True, slots=True)
class AnchorSourceModel:
    """Machine-readable source classification for one identity anchor."""

    source_type: str
    source_quality: str


@dataclass(frozen=True, slots=True)
class DrilldownTarget:
    """Machine-readable drilldown target metadata for one identity anchor."""

    target_type: str
    target_template: str
    label: str
