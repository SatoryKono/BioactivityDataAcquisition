"""Shared types for schema-aware structural policy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

from bioetl.application.core.base_transformer.field_policy import (
    FieldPolicySpec,
)
from bioetl.domain.types import JsonDict, SilverRecord

LogicalType = Literal["string", "integer", "float", "boolean", "unknown"]

@dataclass(frozen=True, slots=True)
class StructuralFieldSpec(FieldPolicySpec):
    """Resolved storage/policy contract for one Silver field."""

    field_name: str
    logical_type: LogicalType
    physical_type: str
    nullable: bool
    is_system_field: bool = False

@dataclass(frozen=True, slots=True)
class StructuralPolicySignal:
    """Log event emitted by structural policy evaluation."""

    level: Literal["warning", "error"]
    event: str
    details: JsonDict

@dataclass(frozen=True, slots=True)
class StructuralPolicyOutcome:
    """Result of applying structural policy to one transformed record."""

    record: SilverRecord
    quarantine_reason: str | None = None
    details: JsonDict | None = None
    events: tuple[StructuralPolicySignal, ...] = ()

    @property
    def should_quarantine(self) -> bool:
        """Whether the record must be routed to quarantine before write."""
        return self.quarantine_reason is not None

@runtime_checkable
class StructuralPolicyProtocol(Protocol):
    """Protocol consumed by BaseTransformer for structural policy checks."""

    def apply(self, record: SilverRecord) -> StructuralPolicyOutcome:
        """Return remediated record or quarantine directive."""
        ...
