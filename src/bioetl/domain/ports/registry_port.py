"""Backward-compatible re-export for runtime registry ports.

Compatibility shim: canonical Port Protocol definitions remain @runtime_checkable
in subpackages and are re-exported here for stable import paths."""

from bioetl.domain.ports.runtime.registry_port import (
    PipelineRegistryPort,
    RegistryAccessorPort,
)

__all__ = ["PipelineRegistryPort", "RegistryAccessorPort"]
