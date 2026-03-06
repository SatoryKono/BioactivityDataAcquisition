"""Backward-compatible re-export for runtime registry ports."""

from bioetl.domain.ports.runtime.registry_port import (
    PipelineRegistryPort,
    RegistryAccessorPort,
)

__all__ = ["PipelineRegistryPort", "RegistryAccessorPort"]
