"""
Pipeline executor that manages state machine for pipeline runs.

This module re-exports from bioetl.application.pipelines.executor
for backward compatibility. New code should import directly from
bioetl.application.pipelines.executor.

Deprecated: Import from bioetl.application.pipelines.executor instead.
"""

from bioetl.application.pipelines.executor import PipelineExecutor

__all__ = ["PipelineExecutor"]
