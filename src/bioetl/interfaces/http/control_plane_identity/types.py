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


# Positional field order after ``priority`` for call sites that still construct
# AnchorSpec with the canonical ordered args (p0/p1/p2 specs modules).
_ANCHOR_SPEC_POSITIONAL_FIELDS: tuple[str, ...] = (
    "name",
    "label",
    "source",
    "value_format",
    "why",
    "rendering",
    "copy",
    "drilldown",
    "missing_severity",
)


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

    def __init__(self, priority: str, *args: object, **fields: object) -> None:
        """Initialize canonical specs while accepting legacy HTTP contract names.

        Accepts either:
        - positional args after ``priority`` in the canonical field order; or
        - kwargs using canonical names (``name``, ``label``, ...) or legacy
          HTTP contract aliases (``anchor_name``, ``display_name``, ...).

        Keeping the surface as ``priority + *args + **fields`` stays under the
        DI/arg-count gate without dropping either construction style.
        """
        if args:
            if len(args) > len(_ANCHOR_SPEC_POSITIONAL_FIELDS):
                raise TypeError(
                    "AnchorSpec() takes at most "
                    f"{len(_ANCHOR_SPEC_POSITIONAL_FIELDS) + 1} positional "
                    f"arguments but {len(args) + 1} were given"
                )
            for key, value in zip(_ANCHOR_SPEC_POSITIONAL_FIELDS, args, strict=False):
                if key in fields:
                    raise TypeError(
                        f"AnchorSpec() got multiple values for argument '{key}'"
                    )
                fields[key] = value
        values = _resolve_anchor_spec_values(priority=priority, **fields)
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
    **fields: object,
) -> dict[str, object]:
    """Resolve canonical AnchorSpec fields from current or legacy aliases.

    Accepts both canonical names (``name``, ``label``, ...) and legacy HTTP
    contract aliases (``anchor_name``, ``display_name``, ...) via kwargs so the
    helper stays under the Sonar S107 parameter budget.
    """
    return {
        "priority": priority,
        "name": _coalesce(fields.get("name"), fields.get("anchor_name")),
        "label": _coalesce(fields.get("label"), fields.get("display_name")),
        "source": _coalesce(fields.get("source"), fields.get("source_location")),
        "value_format": _coalesce(fields.get("value_format"), fields.get("data_type")),
        "why": _coalesce(fields.get("why"), fields.get("description")),
        "rendering": _coalesce(fields.get("rendering"), fields.get("display_mode")),
        "copy": _coalesce(fields.get("copy"), fields.get("is_identifier")),
        "drilldown": _coalesce(fields.get("drilldown"), fields.get("usage_locations")),
        "missing_severity": _resolve_missing_severity(
            fields.get("missing_severity")  # type: ignore[arg-type]
            if fields.get("missing_severity") is None
            or isinstance(fields.get("missing_severity"), str)
            else None,
            fields.get("implementation_status")  # type: ignore[arg-type]
            if fields.get("implementation_status") is None
            or isinstance(fields.get("implementation_status"), str)
            else None,
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
