"""Compatibility shim for lock coordinator imports.

Keeps the historical ``bioetl.application.core.lock_manager`` import path
stable while the implementation lives under ``application.core.lifecycle``.
"""

from __future__ import annotations

from bioetl.application.core.lifecycle.lock_manager import LockCoordinator

__all__ = ["LockCoordinator"]
