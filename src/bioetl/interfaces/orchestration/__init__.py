"""Orchestration utilities for pipeline execution.

Provides:
- register_signal_handlers: Signal handlers for ShutdownPort implementations
"""

from __future__ import annotations

from bioetl.interfaces.orchestration.signals import register_signal_handlers

__all__ = ["register_signal_handlers"]
