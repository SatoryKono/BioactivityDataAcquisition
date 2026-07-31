"""Live multi-process tests for the repository MCP memory server."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any


def _call(process: subprocess.Popen[str], identifier: int, name: str, args: dict[str, Any]) -> Any:
    assert process.stdin is not None
    assert process.stdout is not None
    process.stdin.write(
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": identifier,
                "method": "tools/call",
                "params": {"name": name, "arguments": args},
            }
        )
        + "\n"
    )
    process.stdin.flush()
    return json.loads(process.stdout.readline())["result"]


def _server(path: Path) -> subprocess.Popen[str]:
    env = dict(os.environ, MEMORY_FILE_PATH=str(path))
    return subprocess.Popen(
        [sys.executable, "-m", "memory.mcp_server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )


def test_live_servers_share_scope_persist_and_write_concurrently(tmp_path: Path) -> None:
    path = tmp_path / "shared.json"
    path.write_text('{"entities":[],"relations":[]}\n', encoding="utf-8")
    first, second = _server(path), _server(path)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(
                    _call,
                    process,
                    index,
                    "create_entities",
                    {
                        "entities": [
                            {
                                "name": f"client-{index}",
                                "entityType": "test",
                                "observations": [],
                            }
                        ]
                    },
                )
                for index, process in enumerate((first, second), start=1)
            ]
            for future in futures:
                future.result()
        graph = json.loads(path.read_text(encoding="utf-8"))
        assert {item["name"] for item in graph["entities"]} == {
            "client-1",
            "client-2",
        }
    finally:
        first.terminate()
        second.terminate()
        first.wait(timeout=5)
        second.wait(timeout=5)

    restarted = _server(path)
    try:
        result = _call(restarted, 3, "read_graph", {})
        graph = json.loads(result["content"][0]["text"])
        assert len(graph["entities"]) == 2
    finally:
        restarted.terminate()
        restarted.wait(timeout=5)


def test_live_servers_do_not_cross_scope(tmp_path: Path) -> None:
    paths = [tmp_path / "main.json", tmp_path / "feature.json"]
    for path in paths:
        path.write_text('{"entities":[],"relations":[]}\n', encoding="utf-8")
    servers = [_server(path) for path in paths]
    try:
        _call(
            servers[0],
            1,
            "create_entities",
            {
                "entities": [
                    {"name": "main-only", "entityType": "test", "observations": []}
                ]
            },
        )
        result = _call(servers[1], 2, "read_graph", {})
        assert json.loads(result["content"][0]["text"])["entities"] == []
    finally:
        for process in servers:
            process.terminate()
            process.wait(timeout=5)
