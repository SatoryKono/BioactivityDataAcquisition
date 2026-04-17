"""Backward-compatible imports for Neo4j MCP smoke helpers.

Historically the smoke helpers lived under ``scripts.memory``. The canonical
implementation now lives under ``scripts.ai.mcp.neo4j_memory_mcp_smoke``.
Keep this shim so older tests and entry points continue to import cleanly.
"""

from scripts.ai.mcp.neo4j_memory_mcp_smoke import (
    SmokeResult,
    _encode_frame,
    _parse_frames,
    build_arg_parser,
    main,
    run_smoke_command,
)

__all__ = [
    "SmokeResult",
    "_encode_frame",
    "_parse_frames",
    "build_arg_parser",
    "main",
    "run_smoke_command",
]
