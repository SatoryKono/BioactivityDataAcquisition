"""Compatibility shim for deprecated middleware path."""

from __future__ import annotations

from bioetl.infrastructure.clients.middleware import HttpClientMiddleware

__all__ = ["HttpClientMiddleware"]
