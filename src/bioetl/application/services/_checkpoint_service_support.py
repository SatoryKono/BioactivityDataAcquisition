"""Shared support constants for checkpoint admin observability."""

from __future__ import annotations

_CHECKPOINT_OPERATOR_DURATION_METRIC = "bioetl_checkpoint_operator_duration_seconds"
_CHECKPOINT_OPERATOR_OPERATIONS_METRIC = "bioetl_checkpoint_operator_operations_total"
_CHECKPOINT_OPERATOR_ERRORS = (OSError, RuntimeError, TypeError, ValueError)
