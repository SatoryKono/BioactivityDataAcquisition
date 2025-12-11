"""Pipeline hook and error policy implementations.

This module re-exports from bioetl.application.factories.hooks_impl
for backward compatibility. New code should import directly from
bioetl.application.factories.hooks_impl.

Deprecated: Import from bioetl.application.factories.hooks_impl instead.
"""

from bioetl.application.factories.hooks_impl import (
    ContinueOnErrorPolicyImpl,
    FailFastErrorPolicyImpl,
    LoggingPipelineHookImpl,
    MetricsPipelineHookImpl,
)

__all__ = [
    "LoggingPipelineHookImpl",
    "MetricsPipelineHookImpl",
    "FailFastErrorPolicyImpl",
    "ContinueOnErrorPolicyImpl",
]
