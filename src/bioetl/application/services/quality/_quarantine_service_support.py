"""Shared support constants for quarantine service helpers."""

from __future__ import annotations

_QUARANTINE_OPERATOR_DURATION_METRIC = "bioetl_quarantine_operator_duration_seconds"
_QUARANTINE_OPERATOR_OPERATIONS_METRIC = "bioetl_quarantine_operator_operations_total"
_QUARANTINE_OPERATOR_ERRORS = (OSError, RuntimeError, TypeError, ValueError)
