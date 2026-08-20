"""Pipeline-execution exception tuple shared by batch executor paths."""

from bioetl.application.core.batch_shared_operation_errors import OPERATION_ERRORS

PIPELINE_EXECUTION_ERRORS: tuple[type[Exception], ...] = (*OPERATION_ERRORS,)
