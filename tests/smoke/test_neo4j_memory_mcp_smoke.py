from __future__ import annotations

import sys
from pathlib import Path

import pytest

from scripts.ai.mcp.neo4j_memory_mcp_smoke import (
    _encode_frame,
    _parse_frames,
    run_smoke_command,
)

pytestmark = pytest.mark.memory


def test_parse_frames_round_trips_multiple_messages() -> None:
    payload = b"".join(
        [
            _encode_frame({"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}),
            _encode_frame({"jsonrpc": "2.0", "id": 2, "result": {"tools": []}}),
        ]
    )

    messages = _parse_frames(payload)

    assert messages == [
        {"jsonrpc": "2.0", "id": 1, "result": {"ok": True}},
        {"jsonrpc": "2.0", "id": 2, "result": {"tools": []}},
    ]


def test_parse_frames_rejects_unframed_stdout_preamble() -> None:
    payload = b"oops\n" + _encode_frame(
        {"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}
    )

    try:
        _parse_frames(payload)
    except ValueError as exc:
        assert "Unexpected preamble on MCP stdout" in str(exc)
    else:
        raise AssertionError("Expected invalid preamble to be rejected")


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="MCP smoke test has timeout issues on Windows (platform-specific subprocess behavior)",
)
def test_run_smoke_command_succeeds_against_stub_mcp_server(tmp_path: Path) -> None:
    server = tmp_path / "stub_mcp_server.py"
    server.write_text(
        r"""
from __future__ import annotations

import json
import sys


def read_frame():
    headers = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        if line == b"\r\n":
            break
        name, _, value = line.decode("ascii").partition(":")
        headers[name.strip().lower()] = value.strip()
    content_length = int(headers["content-length"])
    body = sys.stdin.buffer.read(content_length)
    return json.loads(body.decode("utf-8"))


def send_frame(payload):
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    sys.stdout.buffer.write(
        f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body
    )
    sys.stdout.buffer.flush()


while True:
    message = read_frame()
    if message is None:
        break
    if message.get("method") == "initialize":
        send_frame(
            {
                "jsonrpc": "2.0",
                "id": message["id"],
                "result": {
                    "protocolVersion": message["params"]["protocolVersion"],
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "stub", "version": "1.0"},
                },
            }
        )
    elif message.get("method") == "tools/list":
        send_frame(
            {
                "jsonrpc": "2.0",
                "id": message["id"],
                "result": {
                    "tools": [{"name": "search_nodes"}],
                },
            }
        )
        break
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = run_smoke_command([sys.executable, str(server)], timeout_seconds=15.0)

    assert result.ok is True
    assert result.returncode == 0
    assert len(result.responses) == 2
    assert result.responses[0]["id"] == 1
    assert result.responses[1]["id"] == 2


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="MCP smoke test has timeout issues on Windows (platform-specific subprocess behavior)",
)
def test_run_smoke_command_succeeds_when_server_stays_alive_after_handshake(
    tmp_path: Path,
) -> None:
    server = tmp_path / "long_lived_mcp_server.py"
    server.write_text(
        r"""
from __future__ import annotations

import json
import sys


def read_frame():
    headers = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        if line == b"\r\n":
            break
        name, _, value = line.decode("ascii").partition(":")
        headers[name.strip().lower()] = value.strip()
    content_length = int(headers["content-length"])
    body = sys.stdin.buffer.read(content_length)
    return json.loads(body.decode("utf-8"))


def send_frame(payload):
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    sys.stdout.buffer.write(
        f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body
    )
    sys.stdout.buffer.flush()


while True:
    message = read_frame()
    if message is None:
        break
    if message.get("method") == "initialize":
        send_frame(
            {
                "jsonrpc": "2.0",
                "id": message["id"],
                "result": {
                    "protocolVersion": message["params"]["protocolVersion"],
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "stub", "version": "1.0"},
                },
            }
        )
    elif message.get("method") == "tools/list":
        send_frame(
            {
                "jsonrpc": "2.0",
                "id": message["id"],
                "result": {
                    "tools": [{"name": "search_nodes"}],
                },
            }
        )
        sys.stdin.read()
        break
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = run_smoke_command([sys.executable, str(server)], timeout_seconds=5.0)

    assert result.ok is True
    assert result.returncode == 0
    assert len(result.responses) == 2


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="MCP smoke test has timeout issues on Windows (platform-specific subprocess behavior)",
)
def test_run_smoke_command_reports_invalid_stdout_from_wrapper(tmp_path: Path) -> None:
    server = tmp_path / "bad_mcp_server.py"
    server.write_text(
        r"""
from __future__ import annotations

import sys

sys.stdout.write("oops\n")
sys.stdout.flush()
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = run_smoke_command([sys.executable, str(server)], timeout_seconds=5.0)

    assert result.ok is False
    assert "invalid framed output" in result.summary
