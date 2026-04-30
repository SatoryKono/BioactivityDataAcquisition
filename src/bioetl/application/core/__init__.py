"""Pipeline components and base classes.

NOTE: This facade has no active consumers. All symbols should be imported
directly from their defining submodules:

- ``bioetl.application.core.runner``             — PipelineRunner
- ``bioetl.application.core.base``               — BasePipeline
- ``bioetl.application.core.batch_execution``     — Batch-execution lifecycle/run/state helpers
- ``bioetl.application.core.batch_executor``      — BatchExecutor
- ``bioetl.application.core.batch_transformer``   — BatchTransformer, TransformResult
- ``bioetl.application.core.batch_writer``        — BatchWriter
- ``bioetl.application.core.transformer_runtime`` — Batch-transform helper primitives
- ``bioetl.application.core.field_transforms``    — Field specs, dict transforms, entity IDs
- ``bioetl.application.core.lifecycle.checkpoint_manager``  — CheckpointRuntimeService
  (legacy ``CheckpointManager`` and ``CheckpointManagerService`` aliases remain
  only for compatibility in the defining module)
- ``bioetl.application.core.lifecycle.cleanup_service``     — CleanupService, CleanupResult
- ``bioetl.application.core.lifecycle.lock_manager``        — LockCoordinator
- ``bioetl.application.core.lifecycle.shutdown``            — ShutdownService, ShutdownSignal
- ``bioetl.application.core.wiring``                        — composition-facing
  wiring seams for internal DI assembly; flat ``*_wiring_api`` modules remain
  only as compatibility facades
- ``bioetl.application.core.data_sources``                  — specialized
  data-source wrappers; flat ``*_data_source`` modules remain only as
  compatibility facades

Configuration consolidation (all in bioetl.domain.config):
- PipelineConfig: Static pipeline configuration
- RuntimeConfig: CLI/runtime parameters
"""

from __future__ import annotations

__all__: list[str] = []
