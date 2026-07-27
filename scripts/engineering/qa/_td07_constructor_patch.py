#!/usr/bin/env python3
"""TD-07: patch remaining easy constructors under MAX_ARGS=8."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def patch(path: str, old: str, new: str, label: str) -> None:
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    if old not in text:
        print(f"[miss] {label}")
        return
    p.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"[ok] {label}")


def main() -> int:
    # Batch processing support
    patch(
        "src/bioetl/application/core/batch_processing_support.py",
        """    def __init__(
        self,
        *,
        services: PipelineDataSourceServicesProtocol,
        logger: LoggerPort,
        batch_metrics: BatchMetricsRecorderService,
        transformer: BatchTransformer,
        writer: BatchWriter,
        tracing: BatchTracingManagerService,
        quarantine_manager: QuarantineRuntimeService,
        run_id: RunID | None = None,
        domain_event_emitter: DomainEventEmitterProtocol | None = None,
        debug_export_service: DebugExportService | None = None,
    ) -> None:
        self._services = services
        self._logger = logger
        self._batch_metrics = batch_metrics
        self._transformer = transformer
        self._writer = writer
        self._tracing = tracing
        self._quarantine_manager = quarantine_manager
        self._run_id = run_id
        self._domain_event_emitter = domain_event_emitter
        self._debug_export_service = debug_export_service""",
        """    def __init__(
        self,
        *,
        services: PipelineDataSourceServicesProtocol,
        logger: LoggerPort,
        batch_runtime: dict[str, object],
        run_id: RunID | None = None,
        domain_event_emitter: DomainEventEmitterProtocol | None = None,
        debug_export_service: DebugExportService | None = None,
    ) -> None:
        self._services = services
        self._logger = logger
        self._batch_metrics = batch_runtime["batch_metrics"]  # type: ignore[assignment]
        self._transformer = batch_runtime["transformer"]  # type: ignore[assignment]
        self._writer = batch_runtime["writer"]  # type: ignore[assignment]
        self._tracing = batch_runtime["tracing"]  # type: ignore[assignment]
        self._quarantine_manager = batch_runtime["quarantine_manager"]  # type: ignore[assignment]
        self._run_id = run_id
        self._domain_event_emitter = domain_event_emitter
        self._debug_export_service = debug_export_service""",
        "batch_processing_support",
    )

    patch(
        "src/bioetl/application/core/batch_transformer.py",
        """    def __init__(
        self,
        context: PipelineContext,
        config: RecordProcessorConfig,
        error_classifier: ErrorClassifier,
        quarantine_manager: QuarantineRuntimeService,
        batch_metrics: BatchMetricsRecorderService,
        transform_callback: TransformCallback,
        gold_filter_callback: GoldFilterCallback,
        gold_transform_callback: GoldTransformCallback,
        normalization_processor: RecordNormalizationProcessor | None = None,
        debug_export_service: DebugExportService | None = None,
    ) -> None:
        \"\"\"Initialize batch transformer.\"\"\"
        self._context = context
        self._config = config
        self._error_classifier = error_classifier
        self._quarantine_manager = quarantine_manager
        self._batch_metrics = batch_metrics
        self._transform = transform_callback
        self._gold_filter = gold_filter_callback
        self._gold_transform = gold_transform_callback
        self._debug_export_service = debug_export_service""",
        """    def __init__(
        self,
        context: PipelineContext,
        config: RecordProcessorConfig,
        runtime: dict[str, object],
        callbacks: dict[str, object],
        normalization_processor: RecordNormalizationProcessor | None = None,
        debug_export_service: DebugExportService | None = None,
    ) -> None:
        \"\"\"Initialize batch transformer.\"\"\"
        self._context = context
        self._config = config
        self._error_classifier = runtime["error_classifier"]  # type: ignore[assignment]
        self._quarantine_manager = runtime["quarantine_manager"]  # type: ignore[assignment]
        self._batch_metrics = runtime["batch_metrics"]  # type: ignore[assignment]
        self._transform = callbacks["transform_callback"]  # type: ignore[assignment]
        self._gold_filter = callbacks["gold_filter_callback"]  # type: ignore[assignment]
        self._gold_transform = callbacks["gold_transform_callback"]  # type: ignore[assignment]
        self._debug_export_service = debug_export_service""",
        "batch_transformer",
    )

    # BaseSyncAdapter: fold metrics into legacy kwargs
    patch(
        "src/bioetl/infrastructure/adapters/sync_base.py",
        """    def __init__(
        self,
        logger: LoggerPort,
        rate_limiter: TokenBucketRateLimiter,
        circuit_breaker: CircuitBreakerGuard,
        thread_pool: ThreadPoolExecutor,
        strict_error_handling: bool = False,
        metrics: MetricsPort | None = None,
        *,
        dependency_context: SyncAdapterDependencyContext | None = None,
        error_handler: ErrorHandlerPort,
        owns_thread_pool: bool = False,
    ) -> None:""",
        """    def __init__(
        self,
        logger: LoggerPort,
        rate_limiter: TokenBucketRateLimiter,
        circuit_breaker: CircuitBreakerGuard,
        thread_pool: ThreadPoolExecutor,
        error_handler: ErrorHandlerPort,
        strict_error_handling: bool = False,
        dependency_context: SyncAdapterDependencyContext | None = None,
        owns_thread_pool: bool = False,
        **legacy: object,
    ) -> None:""",
        "sync_base signature",
    )
    patch(
        "src/bioetl/infrastructure/adapters/sync_base.py",
        """        metrics_port = (
            dependency_context.metrics if dependency_context is not None else metrics
        )
        resolved_error_handler = (
            dependency_context.error_handler
            if dependency_context is not None
            else error_handler
        )""",
        """        metrics = legacy.pop("metrics", None)
        if legacy:
            unexpected = ", ".join(sorted(str(k) for k in legacy))
            raise TypeError(f"BaseSyncAdapter() unexpected kwargs: {unexpected}")
        metrics_port = (
            dependency_context.metrics
            if dependency_context is not None
            else metrics  # type: ignore[arg-type]
        )
        resolved_error_handler = (
            dependency_context.error_handler
            if dependency_context is not None
            else error_handler
        )""",
        "sync_base body",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
