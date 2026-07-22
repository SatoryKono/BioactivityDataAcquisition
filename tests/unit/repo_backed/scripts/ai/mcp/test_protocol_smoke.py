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
