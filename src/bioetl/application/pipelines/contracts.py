"""Contracts for pipeline components.

This module re-exports application-level pipeline contracts for backwards
compatibility. New code should import directly from bioetl.application.contracts.
"""

from bioetl.application.contracts import PipelineContainerABC, PipelineFactoryABC

__all__ = [
    "PipelineContainerABC",
    "PipelineFactoryABC",
]
