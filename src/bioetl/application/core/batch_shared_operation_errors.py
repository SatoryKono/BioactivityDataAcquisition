"""Shared OPERATION_ERRORS re-export for RF-005 batch runtime consumers.

Keeps the canonical definition in ``batch_operation_errors`` while preventing
a single multi-concern hub from accumulating family-internal fan-in.
"""

from __future__ import annotations

from bioetl.application.core.batch_operation_errors import OPERATION_ERRORS

__all__ = ["OPERATION_ERRORS"]
