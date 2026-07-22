"""Shared types for Control Plane identity evidence.

Legacy HTTP contract compatibility layer - sunset date: 2026-12-31
This module accepts legacy HTTP contract names for backward compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from bioetl.domain.control_plane import RunLedgerEntry

IDENTITY_EVIDENCE_CONTRACT = "control_plane_identity_evidence_v1"

# Legacy HTTP contract compatibility - sunset date: 2026-12-31
# This module accepts legacy HTTP contract names for backward compatibility.
# After sunset, only canonical HTTP contracts should be accepted.


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
        values = _resolve_anchor_spec_values(
            priority=priority,
            name=name,
            label=label,
            source=source,
            value_format=value_format,
            why=why,
            rendering=rendering,
            copy=copy,
            drilldown=drilldown,
            missing_severity=missing_severity,
            anchor_name=anchor_name,
            display_name=display_name,
            source_location=source_location,
            data_type=data_type,
            description=description,
            display_mode=display_mode,
            is_identifier=is_identifier,
            usage_locations=usage_locations,
            implementation_status=implementation_status,
        )
        _apply_anchor_spec_values(self, values)

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


def _coalesce[T](primary: T | None, legacy: T | None) -> T | None:
    """Prefer the canonical field, then the legacy alias."""
    return primary if primary is not None else legacy


def _resolve_missing_severity(
    missing_severity: str | None,
    implementation_status: str | None,
) -> str | None:
    resolved = _coalesce(missing_severity, implementation_status)
    if resolved == "SHIPPED":
        return "INFO"
    return resolved


def _resolve_anchor_spec_values(
    *,
    priority: str,
    name: str | None,
    label: str | None,
    source: str | None,
    value_format: str | None,
    why: str | None,
    rendering: str | None,
    copy: bool | None,
    drilldown: str | None,
    missing_severity: str | None,
    anchor_name: str | None,
    display_name: str | None,
    source_location: str | None,
    data_type: str | None,
    description: str | None,
    display_mode: str | None,
    is_identifier: bool | None,
    usage_locations: str | None,
    implementation_status: str | None,
) -> dict[str, object]:
    return {
        "priority": priority,
        "name": _coalesce(name, anchor_name),
        "label": _coalesce(label, display_name),
        "source": _coalesce(source, source_location),
        "value_format": _coalesce(value_format, data_type),
        "why": _coalesce(why, description),
        "rendering": _coalesce(rendering, display_mode),
        "copy": _coalesce(copy, is_identifier),
        "drilldown": _coalesce(drilldown, usage_locations),
        "missing_severity": _resolve_missing_severity(
            missing_severity,
            implementation_status,
        ),
    }


def _apply_anchor_spec_values(
    instance: AnchorSpec,
    values: dict[str, object],
) -> None:
    missing = [key for key, value in values.items() if value is None]
    if missing:
        fields = ", ".join(missing)
        raise TypeError(f"missing required AnchorSpec fields: {fields}")
    for field_name, value in values.items():
        object.__setattr__(instance, field_name, value)


@dataclass(frozen=True, slots=True)
class AnchorValues:
    """Resolved value for one identity anchor from one control-plane source."""

    spec: AnchorSpec
    value: object
    source: str


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
