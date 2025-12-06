"""
Compatibility shim for logging contracts.

Re-exports LoggerAdapterABC from the new location to keep legacy imports working.
"""

from bioetl.clients.base.logging.contracts import LoggerAdapterABC  # noqa: F401

__all__ = ["LoggerAdapterABC"]
