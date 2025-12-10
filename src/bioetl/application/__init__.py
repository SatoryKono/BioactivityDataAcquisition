"""
Application layer — orchestration and use cases.

Provides core orchestration components for pipeline assembly and execution.

Public API:
    - PipelineContainer: Dependency injection container for pipelines
    - PipelineOrchestrator: High-level orchestration of pipeline execution
    - contracts: Abstract base classes (PipelineContainerABC, PipelineFactoryABC)

For internal components (bootstrap, config loading), import from submodules directly:
    - bioetl.application.bootstrap
    - bioetl.application.config
    - bioetl.application.factories
    - bioetl.application.pipelines
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
