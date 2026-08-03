# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Test support factories for PipelineRunner construction."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.core.runner import PipelineRunner, PipelineRunnerDependencies

if TYPE_CHECKING:
    from bioetl.application.core.lifecycle.checkpoint_manager import (
        CheckpointRuntimeService,
    )
    from bioetl.application.core.lifecycle.lock_runtime_service import (
        LockRuntimeService,
    )
    from bioetl.application.core.lifecycle.shutdown import ShutdownSignal
    from bioetl.application.core.pipeline_observability_service_protocols import (
        PipelineRunnerServicesProtocol,
    )
    from bioetl.application.core.postrun.service import PostrunService
    from bioetl.application.core.preflight.service import PreflightService
    from bioetl.application.observability.observer import PipelineObserver
    from bioetl.application.services.medallion.medallion_lifecycle import (
        MedallionLifecycleService,
    )
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import LoggerPort, TracingPort


def build_test_pipeline_runner(
    *,
    config: PipelineConfig,
    runtime: RuntimeConfig,
    services: PipelineRunnerServicesProtocol,
    context: PipelineContext,
    executor: object,
    checkpoint_manager: CheckpointRuntimeService,
    shutdown_signal: ShutdownSignal,
    lock_manager: LockRuntimeService,
    preflight: PreflightService,
    postrun: PostrunService,
    lifecycle_service: MedallionLifecycleService,
    observer: PipelineObserver,
    tracer: TracingPort,
    logger: LoggerPort | None = None,
) -> PipelineRunner:
    """Build PipelineRunner through the canonical dependency object seam."""
    dependencies = PipelineRunnerDependencies(
        executor=executor,
        checkpoint_manager=checkpoint_manager,
        shutdown_signal=shutdown_signal,
        lock_runtime_service=lock_manager,
        preflight=preflight,
        postrun=postrun,
        lifecycle_service=lifecycle_service,
        observer=observer,
    )
    return PipelineRunner(
        config=config,
        runtime=runtime,
        services=services,
        context=context,
        dependencies=dependencies,
        logger=logger,
        tracer=tracer,
    )
