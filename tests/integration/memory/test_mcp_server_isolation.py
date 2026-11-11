"""Live multi-process tests for the repository MCP memory server."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.integration


def test_stdio_unicode_uses_utf8_despite_parent_encoding(tmp_path: Path) -> None:
    target = tmp_path / ".cache/mcp-memory/graph.json"
    entity = {"name": "unicode", "entityType": "note", "observations": ["я" * 50_000]}
    requests = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "create_entities", "arguments": {"entities": [entity]}},
        },
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "read_graph", "arguments": {"limit": 1}},
        },
    ]
    env = dict(
        os.environ,
        MEMORY_REPO_ROOT=str(tmp_path),
        MEMORY_FILE_PATH=str(target),
        PYTHONIOENCODING="ascii",
    )
    result = subprocess.run(
        [sys.executable, "-m", "memory.mcp_server"],
        input=(
            "\n".join(json.dumps(request, ensure_ascii=False) for request in requests)
            + "\n"
        ).encode("utf-8"),
        env=env,
        capture_output=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    replies = [
        json.loads(line)["result"]
        for line in result.stdout.decode("utf-8").splitlines()
    ]
    assert all(not reply.get("isError") for reply in replies)
    assert json.loads(replies[1]["content"][0]["text"])["entities"] == [entity]


def _call(
    process: subprocess.Popen[str], identifier: int, name: str, args: dict[str, Any]
) -> Any:
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
    source_path = Path(__file__).resolve().parents[3] / "src"
    pythonpath = os.pathsep.join(
        part for part in (str(source_path), os.environ.get("PYTHONPATH")) if part
    )
    repo_root = next(
        parent for parent in path.parents if parent.name == ".cache"
    ).parent
    env = dict(
        os.environ,
        MEMORY_FILE_PATH=str(path),
        MEMORY_REPO_ROOT=str(repo_root),
        PYTHONPATH=pythonpath,
    )
    return subprocess.Popen(
        [sys.executable, "-m", "memory.mcp_server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )


def test_live_servers_share_scope_persist_and_write_concurrently(
    tmp_path: Path,
) -> None:
    path = tmp_path / ".cache" / "mcp-memory" / "shared.json"
    path.parent.mkdir(parents=True)
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
                result = future.result()
                assert not result.get("isError"), result
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
    cache = tmp_path / ".cache" / "mcp-memory"
    cache.mkdir(parents=True)
    paths = [cache / "main.json", cache / "feature.json"]
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
