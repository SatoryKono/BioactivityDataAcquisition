"""Stub factories for pipeline abstractions."""

from bioetl.application.pipelines.contracts import PipelineContainerABC
from bioetl.domain.pipelines.contracts import ErrorPolicyABC, PipelineHookABC, StageABC


def default_pipeline_container() -> PipelineContainerABC:
    """Provide a placeholder pipeline container until DI container is configured."""

    raise NotImplementedError("PipelineContainerABC default factory is not configured")


def default_pipeline_hook() -> PipelineHookABC:
    """Provide a placeholder pipeline hook."""

    raise NotImplementedError("PipelineHookABC default factory is not configured")


def default_error_policy() -> ErrorPolicyABC:
    """Provide a placeholder error policy."""

    raise NotImplementedError("ErrorPolicyABC default factory is not configured")


def default_stage() -> StageABC:
    """Provide a placeholder stage implementation."""

    raise NotImplementedError("StageABC default factory is not configured")


__all__ = [
    "default_pipeline_container",
    "default_pipeline_hook",
    "default_error_policy",
    "default_stage",
]
