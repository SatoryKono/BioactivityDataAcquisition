"""Pipeline-execution exception tuple shared by batch executor paths.

Intentionally excludes KeyError/AttributeError so programming defects surface
instead of being swallowed as recoverable pipeline execution failures.
"""

from __future__ import annotations

from bioetl.application.core.batch_operation_errors import OPERATION_ERRORS

PIPELINE_EXECUTION_ERRORS: tuple[type[Exception], ...] = (*OPERATION_ERRORS,)

__all__ = ["PIPELINE_EXECUTION_ERRORS"]
