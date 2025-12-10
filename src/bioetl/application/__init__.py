"""
Application layer — orchestration and use cases.

Provides core orchestration components for pipeline assembly and execution.

Public API:
    - PipelineContainer: Dependency injection container for pipelines
    - PipelineOrchestrator: High-level pipeline execution coordinator
    - contracts: Abstract base classes (PipelineContainerABC, PipelineFactoryABC)

For bootstrap utilities, import directly from bioetl.application.bootstrap.
For configuration, import from bioetl.application.config.
"""

from bioetl.application import contracts
from bioetl.application.container import PipelineContainer
from bioetl.application.contracts import PipelineContainerABC, PipelineFactoryABC
from bioetl.application.orchestrator import PipelineOrchestrator

__all__ = [
    "PipelineContainer",
    "PipelineContainerABC",
    "PipelineFactoryABC",
    "PipelineOrchestrator",
    "contracts",
]
