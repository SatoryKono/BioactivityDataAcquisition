"""Pipeline registry contract for application/composition callers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from bioetl.domain.ports import PipelineFactoryPort


@runtime_checkable
class PipelineRegistryProtocol(Protocol):
    """Minimal pipeline registry contract required for factory registration."""

    def list_pipelines(self) -> list[str]:
        """Return registered pipeline names."""
        ...

    def register_factory(self, factory: PipelineFactoryPort) -> None:
        """Register one pipeline factory."""
        ...

    def clear(self) -> None:
        """Clear registered factories."""
        ...
