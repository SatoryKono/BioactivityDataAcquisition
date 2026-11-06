"""MCP request isolation and bounded graph access regressions."""

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
