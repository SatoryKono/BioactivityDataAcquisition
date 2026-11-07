"""MCP request isolation and bounded graph access regressions."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from memory import mcp_server

pytestmark = pytest.mark.memory


def test_server_recovers_after_invalid_requests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / ".cache" / "mcp-memory" / "memory.json"
    monkeypatch.setenv("MEMORY_REPO_ROOT", str(tmp_path))
    monkeypatch.setenv("MEMORY_FILE_PATH", str(target))
    requests = [
        "{bad",
        "[]",
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "create_entities",
                    "arguments": {"entities": [None]},
                },
            }
        ),
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "read_graph"},
            }
        ),
    ]
    monkeypatch.setattr(
        mcp_server.sys, "stdin", io.StringIO("\n".join(requests) + "\n")
    )
    assert mcp_server.main() == 0
    replies = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert replies[0]["error"]["code"] == -32700
    assert replies[1]["error"]["code"] == -32600
    assert replies[2]["result"]["isError"] is True
    assert replies[3]["id"] == 2
    assert json.loads(replies[3]["result"]["content"][0]["text"])["entities"] == []
    assert not target.exists()


def test_graph_pages_and_batch_validation(tmp_path: Path) -> None:
    path = tmp_path / ".cache" / "mcp-memory" / "memory.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {"entities": [{"name": str(i)} for i in range(105)], "relations": []}
        ),
        encoding="utf-8",
    )
    store = mcp_server.GraphStore(path, repo_root=tmp_path)
    first = store.call("read_graph", {})
    assert len(first["entities"]) == 100
    assert first["next_offset"] == 100
    assert len(store.call("read_graph", {"offset": 100})["entities"]) == 5
    with pytest.raises(ValueError):
        store.call("read_graph", {"limit": 101})
    with pytest.raises(ValueError):
        store.call("delete_entities", {"entityNames": "all"})


def test_server_rejects_seed_before_any_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed = tmp_path / "seed.json"
    seed.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("MEMORY_REPO_ROOT", str(tmp_path))
    monkeypatch.setenv("MEMORY_FILE_PATH", str(seed))
    assert mcp_server.main() == 64
    assert seed.read_text(encoding="utf-8") == "{}"


def test_oversized_request_does_not_end_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("MEMORY_REPO_ROOT", str(tmp_path))
    monkeypatch.setenv(
        "MEMORY_FILE_PATH", str(tmp_path / ".cache/mcp-memory/graph.json")
    )
    ping = json.dumps({"jsonrpc": "2.0", "id": 7, "method": "ping"})
    monkeypatch.setattr(
        mcp_server.sys,
        "stdin",
        io.StringIO("x" * (mcp_server.MAX_REQUEST_CHARS + 10) + "\n" + ping + "\n"),
    )
    assert mcp_server.main() == 0
    replies = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert replies[0]["error"]["code"] == -32600
    assert replies[1] == {"jsonrpc": "2.0", "id": 7, "result": {}}


@pytest.mark.parametrize("character", ["я", "😀"])
def test_large_unicode_entity_remains_readable(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], character: str
) -> None:
    target = tmp_path / ".cache/mcp-memory/graph.json"
    store = mcp_server.GraphStore(target, repo_root=tmp_path)
    entity = {
        "name": "unicode",
        "entityType": "note",
        "observations": [character * 50_000],
    }
    for identifier, name, arguments in (
        (1, "create_entities", {"entities": [entity]}),
        (2, "read_graph", {"limit": 1}),
    ):
        mcp_server._handle(
            store,
            {
                "jsonrpc": "2.0",
                "id": identifier,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            },
        )
    replies = [
        json.loads(line)["result"] for line in capsys.readouterr().out.splitlines()
    ]
    assert all(not reply.get("isError") for reply in replies)
    assert json.loads(replies[1]["content"][0]["text"])["entities"] == [entity]


def test_response_limit_rejects_mutation_before_commit(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / ".cache/mcp-memory/graph.json"
    store = mcp_server.GraphStore(target, repo_root=tmp_path)
    store.call(
        "create_entities",
        {"entities": [{"name": "existing", "entityType": "note", "observations": []}]},
    )
    before = target.read_bytes()
    mcp_server._handle(
        store,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "create_entities",
                "arguments": {
                    "entities": [
                        {
                            "name": "too-large",
                            "entityType": "note",
                            "observations": ["я" * mcp_server.MAX_REQUEST_CHARS],
                        }
                    ]
                },
            },
        },
    )
    assert json.loads(capsys.readouterr().out)["result"]["isError"] is True
    assert target.read_bytes() == before
    assert store.call("read_graph", {"limit": 1})["entities"][0]["name"] == "existing"


@pytest.mark.parametrize("headroom", [120, 180, 240])
def test_response_boundary_never_persists_an_unreadable_entity(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], headroom: int
) -> None:
    target = tmp_path / ".cache/mcp-memory/graph.json"
    store = mcp_server.GraphStore(target, repo_root=tmp_path)
    entity = {
        "name": "edge",
        "entityType": "note",
        "observations": ["x" * (mcp_server.MAX_REQUEST_CHARS - headroom)],
    }
    try:
        store.call("create_entities", {"entities": [entity]})
    except ValueError:
        assert not target.exists()
    else:
        mcp_server._handle(
            store,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "read_graph", "arguments": {"limit": 1}},
            },
        )
        result = json.loads(capsys.readouterr().out)["result"]
        assert not result.get("isError")
        assert json.loads(result["content"][0]["text"])["entities"] == [entity]
