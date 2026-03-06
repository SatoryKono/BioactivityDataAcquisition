"""Backward-compatible re-export for runtime runner ports.

Compatibility shim: canonical Port Protocol definitions remain @runtime_checkable
in subpackages and are re-exported here for stable import paths."""

from bioetl.domain.ports.runtime.runner import (
    MetricsExtractorPort,
    PipelineFactoryPort,
    RunnablePort,
    RunnerFactoryPort,
)

__all__ = [
    "MetricsExtractorPort",
    "PipelineFactoryPort",
    "RunnablePort",
    "RunnerFactoryPort",
]
