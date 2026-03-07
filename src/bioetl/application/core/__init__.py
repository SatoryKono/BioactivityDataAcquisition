"""Pipeline components and base classes.

NOTE: This facade has no active consumers. All symbols should be imported
directly from their defining submodules:

- ``bioetl.application.core.runner``             — PipelineRunner
- ``bioetl.application.core.base``               — BasePipeline
- ``bioetl.application.core.batch_executor``      — BatchExecutor
- ``bioetl.application.core.batch_transformer``   — BatchTransformer, TransformResult
- ``bioetl.application.core.batch_writer``        — BatchWriter
- ``bioetl.application.core.checkpoint_manager``  — CheckpointManager
- ``bioetl.application.core.cleanup_service``     — CleanupService, CleanupResult
- ``bioetl.application.core.lock_manager``        — LockCoordinator
- ``bioetl.application.core.shutdown``            — ShutdownService, ShutdownSignal

Configuration consolidation (all in bioetl.domain.config):
- PipelineConfig: Static pipeline configuration
- RuntimeConfig: CLI/runtime parameters
"""

from __future__ import annotations

__all__: list[str] = []
