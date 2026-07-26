from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from scripts.ai.mcp import protocol_smoke

pytestmark = pytest.mark.repo_backed


class _Input:
    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

    def write(self, value: str) -> int:
        self.messages.append(json.loads(value))
        return len(value)

    def flush(self) -> None:
        return None


class _Output:
    def readline(self) -> str:
        return ""


class _StderrChunks:
    def __init__(self, value: str) -> None:
        self._value = value
        self._offset = 0

    def read(self, size: int = -1) -> str:
        if self._offset >= len(self._value):
            return ""
        if size < 0:
            size = len(self._value) - self._offset
        chunk = self._value[self._offset : self._offset + size]
        self._offset += len(chunk)
        return chunk


class _Process:
    def __init__(self, stderr: Any | None = None) -> None:
        self.stdin = _Input()
        self.stdout = _Output()
        self.stderr = [] if stderr is None else stderr

    def terminate(self) -> None:
        return None

    def wait(self, timeout: float) -> int:
        return 0

    def kill(self) -> None:
        return None


def test_smoke_http_shared_plane_ping(
    monkeypatch: Any, tmp_path: Path
) -> None:
    """HTTP shared-plane smoke: localhost url → ping (+ optional initialize)."""
    config = tmp_path / ".cursor-mcp.json"
    config.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "adr-analysis": {
                        "type": "http",
                        "url": "http://127.0.0.1:8813/mcp",
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    class _Resp:
        def __init__(self, body: bytes = b"ok", status: int = 200) -> None:
            self._body = body
            self.status = status

        def read(self) -> bytes:
            return self._body

        def __enter__(self) -> "_Resp":
            return self

        def __exit__(self, *args: object) -> None:
            return None

    calls: list[str] = []

    def fake_urlopen(req: Any, timeout: float = 0) -> _Resp:
        url = req if isinstance(req, str) else req.full_url
        calls.append(str(url))
        if str(url).endswith("/ping"):
            return _Resp(b"ok")
        # initialize JSON body
        return _Resp(
            json.dumps(
                {"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "1"}}
            ).encode()
        )

    import urllib.request

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    report = protocol_smoke.smoke_server(config, "adr-analysis", timeout=1)
    assert report["ok"] is True
    assert report["transport"] == "http"
    assert report["initialize_ok"] is True
    assert any(c.endswith("/ping") for c in calls)


def test_smoke_http_rejects_non_localhost(tmp_path: Path) -> None:
    config = tmp_path / "mcp.json"
    config.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "evil": {"type": "http", "url": "https://evil.example/mcp"}
                }
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="localhost"):
        protocol_smoke.smoke_server(config, "evil", timeout=1)


def test_smoke_performs_initialize_and_tools_list(
    monkeypatch: Any, tmp_path: Path
) -> None:
    config = tmp_path / ".mcp.json"
    config.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "example": {
                        "command": "example-server",
                        "args": ["--stdio"],
                        "env": {"EXAMPLE_TOKEN": "secret-must-not-be-reported"},
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    process = _Process()
    responses = iter(
        [
            {"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "1"}},
            {"jsonrpc": "2.0", "id": 2, "result": {"tools": [{"name": "x"}]}},
        ]
    )
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(
        protocol_smoke,
        "_readline",
        lambda stream, timeout: json.dumps(next(responses)),
    )

    report = protocol_smoke.smoke_server(config, "example", timeout=1)

    assert report["ok"] is True
    assert report["tool_count"] == 1
    assert report["environment_names"] == ["EXAMPLE_TOKEN"]
    assert "secret-must-not-be-reported" not in json.dumps(report)
    assert [message.get("method") for message in process.stdin.messages] == [
        "initialize",
        "notifications/initialized",
        "tools/list",
    ]


def test_smoke_stderr_tail_is_character_bounded_after_shutdown(
    monkeypatch: Any, tmp_path: Path
) -> None:
    config = tmp_path / ".mcp.json"
    config.write_text(
        json.dumps({"mcpServers": {"example": {"command": "example-server"}}}),
        encoding="utf-8",
    )
    payload = (
        "DROP-ME" + "A" * (protocol_smoke._STDERR_RETENTION_CHARS + 5000) + "KEEP-ME"
    )
    process = _Process(stderr=_StderrChunks(payload))
    responses = iter(
        [
            {"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "1"}},
            {"jsonrpc": "2.0", "id": 2, "result": {"tools": "invalid"}},
        ]
    )
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(
        protocol_smoke,
        "_readline",
        lambda stream, timeout: json.dumps(next(responses)),
    )

    with pytest.raises(RuntimeError) as exc_info:
        protocol_smoke.smoke_server(config, "example", timeout=1)

    message = str(exc_info.value)
    assert "stderr_tail=" in message
    assert "KEEP-ME" in message
    assert "DROP-ME" not in message
    assert len(message) < protocol_smoke._STDERR_ERROR_TAIL_CHARS + 500


@pytest.mark.parametrize(
    ("name", "content"),
    [
        (
            "vscode.json",
            json.dumps({"servers": {"example": {"command": "server"}}}),
        ),
        (
            "codex.toml",
            '[mcp_servers.example]\ncommand = "server"\nargs = []\n',
        ),
    ],
)
def test_supported_frontend_projections_use_the_same_protocol_smoke(
    monkeypatch: Any, tmp_path: Path, name: str, content: str
) -> None:
    config = tmp_path / name
    config.write_text(content, encoding="utf-8")
    process = _Process()
    responses = iter(
        [
            {"jsonrpc": "2.0", "id": 1, "result": {}},
            {"jsonrpc": "2.0", "id": 2, "result": {"tools": []}},
        ]
    )
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(
        protocol_smoke,
        "_readline",
        lambda stream, timeout: json.dumps(next(responses)),
    )

    assert protocol_smoke.smoke_server(config, "example", timeout=1)["ok"] is True
