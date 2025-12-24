"""Orchestration utilities for pipeline execution.

Provides:
- setup_shutdown_handlers: Signal handlers for graceful shutdown
"""

from __future__ import annotations

from bioetl.interfaces.orchestration.signals import setup_shutdown_handlers

__all__ = ["setup_shutdown_handlers"]
