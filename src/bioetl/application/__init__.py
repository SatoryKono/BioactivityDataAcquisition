"""
Application layer package.

Provides core orchestration components for pipeline assembly and execution.
"""

from bioetl.application.container import PipelineContainer, create_default_container_factory
from bioetl.application.orchestrator import PipelineOrchestrator

__all__ = [
    "PipelineContainer",
    "PipelineOrchestrator",
    "create_default_container_factory",
]
