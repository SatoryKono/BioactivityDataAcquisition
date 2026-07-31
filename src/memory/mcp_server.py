"""Repository-owned, lock-safe stdio MCP server for file-backed memory."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from memory.storage import (
    StorageConflictError,
    atomic_write_json,
    content_digest,
)


class GraphStore:
    """Optimistic, atomic graph store safe across MCP server processes."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def read(self) -> dict[str, list[dict[str, Any]]]:
        if not self.path.exists():
            return {"entities": [], "relations": []}
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return {
            "entities": list(payload.get("entities", [])),
            "relations": list(payload.get("relations", [])),
        }

    def update(
        self, operation: Callable[[dict[str, list[dict[str, Any]]]], Any]
    ) -> Any:
        for _ in range(100):
            raw = self.path.read_bytes() if self.path.exists() else b""
            graph = json.loads(raw) if raw else {"entities": [], "relations": []}
            result = operation(graph)
            try:
                atomic_write_json(
                    self.path,
                    graph,
                    expected_digest=content_digest(raw),
                )
                return result
            except StorageConflictError:
                continue
        raise StorageConflictError("MCP memory update retry budget exhausted")

    def call(self, name: str, arguments: dict[str, Any]) -> Any:
        if name == "read_graph":
            return self.read()
        if name == "create_entities":
            entities = list(arguments.get("entities", []))

            def create(graph: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
                existing = {item["name"] for item in graph["entities"]}
                added = [item for item in entities if item["name"] not in existing]
                graph["entities"].extend(added)
                return added

            return self.update(create)
        if name == "delete_entities":
            names = set(arguments.get("entityNames", []))

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
        raise ValueError(f"unsupported tool: {name}")


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
        "description": "Read the complete graph.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def _reply(identifier: Any, result: Any) -> None:
    print(
        json.dumps({"jsonrpc": "2.0", "id": identifier, "result": result}), flush=True
    )


def main() -> int:
    target = os.environ.get("MEMORY_FILE_PATH")
    if not target:
        print("MEMORY_FILE_PATH is required", file=sys.stderr)
        return 64
    store = GraphStore(Path(target))
    for line in sys.stdin:
        request = json.loads(line)
        identifier = request.get("id")
        method = request.get("method")
        if method == "initialize":
            _reply(
                identifier,
                {
                    "protocolVersion": request.get("params", {}).get(
                        "protocolVersion", "2025-03-26"
                    ),
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "bioetl-memory", "version": "1"},
                },
            )
        elif method == "tools/list":
            _reply(identifier, {"tools": _TOOLS})
        elif method == "tools/call":
            params = request.get("params", {})
            value = store.call(params["name"], params.get("arguments", {}))
            _reply(
                identifier,
                {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(value, ensure_ascii=False),
                        }
                    ]
                },
            )
        elif identifier is not None:
            _reply(identifier, {})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
