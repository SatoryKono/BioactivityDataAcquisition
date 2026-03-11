"""Compatibility shim for shutdown imports.

Keeps the historical ``bioetl.application.core.shutdown`` import path
stable while the implementation lives under ``application.core.lifecycle``.
"""

from __future__ import annotations

from bioetl.application.core.lifecycle.shutdown import (
    PipelineShutdownError,
    ShutdownReason,
    ShutdownService,
    ShutdownSignal,
)

__all__ = [
    "PipelineShutdownError",
    "ShutdownReason",
    "ShutdownService",
    "ShutdownSignal",
]
