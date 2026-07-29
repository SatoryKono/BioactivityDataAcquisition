"""Shared typing contracts for base transformer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, runtime_checkable

from bioetl.application.core.base_transformer.structural_policy import (
    StructuralPolicyProtocol,
)
from bioetl.domain.behavior import EntityIdentityGenerator
from bioetl.domain.ports import (
    ContractPolicyProtocol,
    DataNormalizationPort,
    MetricsPort,
    PiiHasherPort,
    TracingPort,
)

if TYPE_CHECKING:
    from bioetl.domain.entities import BaseEntity

T = TypeVar("T", bound="BaseEntity")
V = TypeVar("V", covariant=True)


@dataclass(frozen=True, slots=True)
class TransformerDependencyContext:
    """Explicit collaborator bundle for ``BaseTransformer`` wiring.
    The transformer core consumes this contract, while composition remains the
    owner of concrete runtime defaults.
    """
    tracer: TracingPort
    metrics: MetricsPort
    identity_service: EntityIdentityGenerator
    pii_hasher: PiiHasherPort
    data_normalizer: DataNormalizationPort
    contract_policy: ContractPolicyProtocol
    structural_policy: StructuralPolicyProtocol


@runtime_checkable
class ValueObjectWithFromRaw(Protocol[V]):
    """Protocol for Value Objects exposing ``from_raw`` and ``value``."""
    @classmethod
    def from_raw(cls, raw: Any) -> V | None:  # Any: raw input
        """Create a value object from a raw input, returning None if invalid."""
        ...
    @property
    def value(self) -> Any:  # Any: VO value type varies (str | int | float)
        """Return the unwrapped primitive value of the value object."""
        ...
