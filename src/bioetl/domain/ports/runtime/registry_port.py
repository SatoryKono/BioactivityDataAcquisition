"""Registry port protocols for dependency inversion.

Defines contracts for pipeline registry access.
Migrated from application/services/config_service.py per RF-040 (ARCH-008).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

__all__ = [
    "PipelineRegistryPort",
    "RegistryAccessorPort",
]


@runtime_checkable
class PipelineRegistryPort(Protocol):
    """Protocol for pipeline registry."""

    def list_pipelines(self) -> list[str]:
        """List all registered pipeline names.

        Returns:
            Collection of pipelines.
        """
        ...


@runtime_checkable
class RegistryAccessorPort(Protocol):
    """Protocol for accessing the pipeline registry."""

    def __call__(self) -> PipelineRegistryPort:
        """Access registry."""
        ...
