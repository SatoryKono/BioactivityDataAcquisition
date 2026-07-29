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
"""Shared PostrunService test support helpers."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import TYPE_CHECKING

from bioetl.application.core.postrun.service import PostrunService
from bioetl.composition.factories.pipeline.postrun_assembly import (
    build_postrun_dependency_context,
)
from bioetl.domain.ports.noop import (
    NoOpMetrics,
    NoOpTracing,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


@dataclass(frozen=True)
class PostrunDependencyOverrides:
    """Optional dependency overrides for PostrunService test assembly."""

    metadata_coordinator: object | None = None
    metadata_writer: object | None = None
    dq_report_service: object | None = None
    bronze_dq_config: object | None = None
    silver_dq_config: object | None = None
    gold_dq_config: object | None = None


_DEPENDENCY_OVERRIDE_FIELDS = frozenset(PostrunDependencyOverrides.__dataclass_fields__)


def _resolve_dependency_overrides(
    overrides: PostrunDependencyOverrides | None,
    dependency_kwargs: dict[str, object],
) -> PostrunDependencyOverrides:
    unknown_keys = set(dependency_kwargs) - _DEPENDENCY_OVERRIDE_FIELDS
    if unknown_keys:
        unknown = ", ".join(sorted(unknown_keys))
        raise TypeError(f"unknown postrun dependency override(s): {unknown}")
    if overrides is not None and dependency_kwargs:
        raise TypeError("pass either overrides or direct dependency kwargs, not both")
    return overrides or PostrunDependencyOverrides(**dependency_kwargs)


def build_test_postrun_service(
    *,
    config: object,
    runtime: object,
    context: object,
    dq_service: object,
    lifecycle_service: object,
    storage: object,
    logger: LoggerPort,
    metrics: object | None = None,
    tracer: object | None = None,
    overrides: PostrunDependencyOverrides | None = None,
    **dependency_kwargs: object,
) -> PostrunService:
    """Build PostrunService with explicit injected collaborators for tests.

    The helper accepts either a pre-built ``overrides`` bundle or direct keyword
    overrides for older tests that injected collaborators individually.
    """
    dependency_overrides = _resolve_dependency_overrides(overrides, dependency_kwargs)
    return PostrunService(
        config=config,
        runtime=runtime,
        context=context,
        dq_service=dq_service,
        lifecycle_service=lifecycle_service,
        tracer=tracer if tracer is not None else NoOpTracing(),
        dependencies=build_postrun_dependency_context(
            config=config,
            runtime=runtime,
            context=context,
            storage=storage,
            logger_port=logger,
            dq_report_service=dependency_overrides.dq_report_service,
            bronze_dq_config=dependency_overrides.bronze_dq_config,
            silver_dq_config=dependency_overrides.silver_dq_config,
            gold_dq_config=dependency_overrides.gold_dq_config,
            metadata_coordinator=dependency_overrides.metadata_coordinator,
            metadata_writer=dependency_overrides.metadata_writer,
        ),
        services=SimpleNamespace(
            storage=storage,
            metrics=metrics if metrics is not None else NoOpMetrics(warn_on_use=False),
            logger=logger,
            metadata_coordinator=dependency_overrides.metadata_coordinator,
            metadata_writer=dependency_overrides.metadata_writer,
        ),
    )
