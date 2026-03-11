"""Compatibility shim for heartbeat imports.

Keeps the historical ``bioetl.application.core.heartbeat`` import path
stable while the implementation lives under ``application.core.lifecycle``.
"""

from __future__ import annotations

from bioetl.application.core.lifecycle.heartbeat import HeartbeatTask

__all__ = ["HeartbeatTask"]
