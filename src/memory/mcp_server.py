"""Repository-owned, lock-safe stdio MCP server for file-backed memory."""

from __future__ import annotations

import json
import os
import sys
import time
from collections.abc import Callable
from io import TextIOWrapper
from pathlib import Path
from typing import Any

from memory.mcp_scope import validate_memory_target
from memory.storage import (
    StorageConflictError,
    atomic_write_json,
    content_digest,
)

MAX_REQUEST_CHARS = 262_144
MAX_GRAPH_BYTES = 4_194_304
MAX_BATCH = 100
MAX_PAGE = 100


def _tool_result(value: Any) -> dict[str, Any]:
    result = {
        "content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False)}]
    }
    if len(json.dumps(result, ensure_ascii=False).encode("utf-8")) > MAX_REQUEST_CHARS:
        raise ValueError("MCP response exceeds limit; request a smaller page")
    return result


def _graph_page(
    graph: dict[str, list[dict[str, Any]]], offset: int, limit: int
) -> dict[str, Any]:
    return {
        **{key: rows[offset : offset + limit] for key, rows in graph.items()},
        "totals": {key: len(rows) for key, rows in graph.items()},
        "next_offset": offset + limit
        if any(len(rows) > offset + limit for rows in graph.values())
        else None,
    }


class GraphStore:
    """Optimistic, atomic graph store safe across MCP server processes."""

    def __init__(self, path: Path, *, repo_root: Path | None = None) -> None:
        self.repo_root = repo_root or Path(__file__).resolve().parents[2]
        self.path = validate_memory_target(path, self.repo_root)

    def _raw(self) -> bytes:
        validate_memory_target(self.path, self.repo_root)
        if not self.path.exists():
            return b""
        with self.path.open("rb") as stream:
            raw = stream.read(MAX_GRAPH_BYTES + 1)
        if len(raw) > MAX_GRAPH_BYTES:
            raise ValueError("MCP memory graph exceeds size limit")
        return raw

    def read(self) -> dict[str, list[dict[str, Any]]]:
        raw = self._raw()
        payload = json.loads(raw) if raw else {"entities": [], "relations": []}
        if not isinstance(payload, dict) or any(
            not isinstance(payload.get(key), list) for key in ("entities", "relations")
        ):
            raise ValueError("MCP memory graph must contain entity and relation arrays")
        return {
            "entities": list(payload.get("entities", [])),
            "relations": list(payload.get("relations", [])),
        }

    def update(
        self, operation: Callable[[dict[str, list[dict[str, Any]]]], Any]
    ) -> Any:
        deadline = time.monotonic() + 5.0
        for _ in range(16):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            raw = self._raw()
            graph = json.loads(raw) if raw else {"entities": [], "relations": []}
            result = operation(graph)
            if (
                len(
                    (
                        json.dumps(graph, ensure_ascii=False, indent=2, sort_keys=True)
                        + "\n"
                    ).encode("utf-8")
                )
                > MAX_GRAPH_BYTES
            ):
                raise ValueError("MCP memory graph exceeds size limit")
            # Validate both the mutation result and the smallest readable pages
            # before committing; rejected calls must leave the stored graph intact.
            _tool_result(result)
            for offset in range(max(len(rows) for rows in graph.values())):
                _tool_result(_graph_page(graph, offset, 1))
            try:
                atomic_write_json(
                    self.path,
                    graph,
                    expected_digest=content_digest(raw),
                    lock_timeout_seconds=remaining,
                )
                return result
            except StorageConflictError:
                continue
        raise StorageConflictError("MCP memory update retry budget exhausted")

    def call(self, name: str, arguments: dict[str, Any]) -> Any:
        if name == "read_graph":
            return self._read_graph(arguments)
        if name == "create_entities":
            return self._create_entities(arguments.get("entities"))
        if name == "delete_entities":
            return self._delete_entities(arguments.get("entityNames"))
        raise ValueError(f"unsupported tool: {name}")

    def _read_graph(self, arguments: dict[str, Any]) -> dict[str, Any]:
        offset = arguments.get("offset", 0)
        limit = arguments.get("limit", MAX_PAGE)
        if (
            type(offset) is not int
            or offset < 0
            or type(limit) is not int
            or not 1 <= limit <= MAX_PAGE
        ):
            raise ValueError("read_graph requires offset >= 0 and limit in 1..100")
        return _graph_page(self.read(), offset, limit)

    def _delete_entities(self, values: Any) -> Any:
        if (
            not isinstance(values, list)
            or len(values) > MAX_BATCH
            or any(not isinstance(value, str) for value in values)
        ):
            raise ValueError("entityNames must contain at most 100 strings")
        names = set(values)

        def delete(graph: dict[str, list[dict[str, Any]]]) -> None:
            graph["entities"] = [
                item for item in graph["entities"] if item["name"] not in names
            ]
            graph["relations"] = [
                item
                for item in graph["relations"]
                if item["from"] not in names and item["to"] not in names
            ]

        return self.update(delete)

    @staticmethod
    def _is_valid_entity(item: Any) -> bool:
        return (
            isinstance(item, dict)
            and isinstance(item.get("name"), str)
            and bool(item["name"])
            and isinstance(item.get("entityType"), str)
            and isinstance(item.get("observations"), list)
            and all(isinstance(value, str) for value in item["observations"])
        )

    def _create_entities(self, entities: Any) -> Any:
        if (
            not isinstance(entities, list)
            or len(entities) > MAX_BATCH
            or any(not self._is_valid_entity(item) for item in entities)
        ):
            raise ValueError("entities must contain at most 100 valid graph entities")

        def create(graph: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
            existing = {item["name"] for item in graph["entities"]}
            added = []
            for item in entities:
                if item["name"] not in existing:
                    existing.add(item["name"])
                    added.append(item)
            graph["entities"].extend(added)
            return added

        return self.update(create)


_TOOLS = [
    {
        "name": "create_entities",
        "description": "Create graph entities atomically.",
        "inputSchema": {
            "type": "object",
            "properties": {"entities": {"type": "array"}},
        },
    },
    {
        "name": "delete_entities",
        "description": "Delete graph entities atomically.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entityNames": {"type": "array", "items": {"type": "string"}}
            },
        },
    },
    {
        "name": "read_graph",
        "description": "Read a bounded page of entities and relations; follow next_offset.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "offset": {"type": "integer", "minimum": 0},
                "limit": {"type": "integer", "minimum": 1, "maximum": MAX_PAGE},
            },
        },
    },
]


def _reply(identifier: Any, result: Any) -> None:
    response = json.dumps(
        {"jsonrpc": "2.0", "id": identifier, "result": result}, ensure_ascii=False
    )
    print(response.encode("utf-8", "backslashreplace").decode("utf-8"), flush=True)


def _error(identifier: Any, code: int, message: str) -> None:
    print(
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": identifier,
                "error": {"code": code, "message": message},
            }
        ),
        flush=True,
    )


def _handle(store: GraphStore, request: Any) -> None:
    if (
        not isinstance(request, dict)
        or request.get("jsonrpc") != "2.0"
        or not isinstance(request.get("method"), str)
    ):
        _error(None, -32600, "Invalid Request")
        return
    if "id" not in request:
        return
    identifier = request["id"]
    params = request.get("params", {})
    if not isinstance(params, dict):
        _error(identifier, -32602, "Invalid params")
        return
    method = request["method"]
    if method == "initialize":
        _reply(
            identifier,
            {
                "protocolVersion": params.get("protocolVersion", "2025-03-26"),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "bioetl-memory", "version": "1"},
            },
        )
    elif method == "ping":
        _reply(identifier, {})
    elif method == "tools/list":
        _reply(identifier, {"tools": _TOOLS})
    elif method == "tools/call":
        arguments = params.get("arguments", {})
        if not isinstance(params.get("name"), str) or not isinstance(arguments, dict):
            _error(identifier, -32602, "Invalid tool parameters")
            return
        try:
            result = _tool_result(store.call(params["name"], arguments))
        except (ValueError, KeyError, TypeError, OSError, StorageConflictError):
            result = {
                "isError": True,
                "content": [
                    {
                        "type": "text",
                        "text": "Memory operation failed: invalid data, storage conflict or resource limit",
                    }
                ],
            }
        _reply(identifier, result)
    else:
        _error(identifier, -32601, "Method not found")


def _configure_stdio() -> None:
    for stream in (sys.stdin, sys.stdout):
        if isinstance(stream, TextIOWrapper):
            stream.reconfigure(encoding="utf-8")


def _open_store() -> GraphStore | None:
    target = os.environ.get("MEMORY_FILE_PATH")
    if not target:
        print("MEMORY_FILE_PATH is required", file=sys.stderr)
        return None
    root = Path(os.environ.get("MEMORY_REPO_ROOT", Path(__file__).resolve().parents[2]))
    try:
        return GraphStore(Path(target), repo_root=root)
    except ValueError:
        print(
            "MEMORY_FILE_PATH must be inside repository .cache/mcp-memory",
            file=sys.stderr,
        )
        return None


def _discard_oversized_request(line: str) -> None:
    while not line.endswith("\n"):
        line = sys.stdin.readline(MAX_REQUEST_CHARS + 1)
        if not line:
            break
    _error(None, -32600, "Request exceeds size limit")


def _handle_request_line(store: GraphStore, line: str) -> None:
    try:
        request = json.loads(line)
    except (ValueError, RecursionError):
        _error(None, -32700, "Parse error")
        return
    try:
        _handle(store, request)
    except RecursionError:
        _error(
            request.get("id") if isinstance(request, dict) else None,
            -32602,
            "Parameters exceed nesting limit",
        )


def main() -> int:
    _configure_stdio()
    store = _open_store()
    if store is None:
        return 64
    while line := sys.stdin.readline(MAX_REQUEST_CHARS + 1):
        if len(line) > MAX_REQUEST_CHARS:
            _discard_oversized_request(line)
            continue
        _handle_request_line(store, line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
