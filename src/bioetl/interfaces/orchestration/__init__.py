"""Orchestration utilities for pipeline execution.

Provides:
- register_signal_handlers: Signal handlers for ShutdownService (recommended)
- setup_shutdown_handlers: Signal handlers for ShutdownSignal (deprecated)
"""

from __future__ import annotations

from bioetl.interfaces.orchestration.signals import (
    register_signal_handlers,
    setup_shutdown_handlers,
)

__all__ = ["register_signal_handlers", "setup_shutdown_handlers"]
