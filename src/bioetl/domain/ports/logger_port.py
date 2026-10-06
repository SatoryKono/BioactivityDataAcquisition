"""Compatibility re-export for the canonical structured logging port."""

from __future__ import annotations

from bioetl.domain.ports.observability.logging import LoggerPort

__all__ = ["LoggerPort"]

# LoggerPort remains a @runtime_checkable Protocol from observability.logging.
