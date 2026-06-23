"""Backward-compatible lazy imports for Neo4j MCP smoke helpers.

Historically the smoke helpers lived under ``scripts.memory``. The canonical
implementation now lives under ``scripts.ai.mcp.neo4j_memory_mcp_smoke``.
Keep this shim so older tests and entry points continue to import cleanly.
"""

from importlib import import_module
from typing import Any

_EXPORTS = frozenset(
    {
        "SmokeResult",
        "_encode_frame",
        "_parse_frames",
        "build_arg_parser",
        "main",
        "run_smoke_command",
    }
)


def _impl() -> Any:
    return import_module("scripts.ai.mcp.neo4j_memory_mcp_smoke")


def __getattr__(name: str) -> object:
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(_impl(), name)


__all__ = [
    "SmokeResult",
    "_encode_frame",
    "_parse_frames",
    "build_arg_parser",
    "main",
    "run_smoke_command",
]
