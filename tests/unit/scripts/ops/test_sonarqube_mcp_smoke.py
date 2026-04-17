from __future__ import annotations

import sys
from pathlib import Path

from scripts.ai.mcp.sonarqube_mcp_smoke import (
    _STDIO_PROTOCOL_VERSION,
    run_smoke_command,
)


def test_run_smoke_command_succeeds_against_ready_then_line_delimited_stub(tmp_path: Path) -> None:
    server = tmp_path / "sonar_line_stub_server.py"
    server.write_text(
        f"""
from __future__ import annotations

import json
import sys


def send_message(payload):
    sys.stdout.write(json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\\n")
    sys.stdout.flush()


sys.stderr.write("INFO SonarQube MCP Server - Status: Server ready\\n")
sys.stderr.flush()

while True:
    line = sys.stdin.readline()
    if not line:
        break
    message = json.loads(line)
    if message.get("method") == "initialize":
        send_message(
            {{
                "jsonrpc": "2.0",
                "id": message["id"],
                "result": {{
                    "protocolVersion": "{_STDIO_PROTOCOL_VERSION}",
                    "capabilities": {{"tools": {{}}}},
                    "serverInfo": {{"name": "sonar-line-stub", "version": "1.0"}},
                }},
            }}
        )
    elif message.get("method") == "tools/list":
        send_message(
            {{
                "jsonrpc": "2.0",
                "id": message["id"],
                "result": {{"tools": [{{"name": "search_my_sonarqube_projects"}}]}},
            }}
        )
        break
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = run_smoke_command(
        [sys.executable, str(server)],
        startup_timeout_seconds=5.0,
        handshake_timeout_seconds=5.0,
    )

    assert result.ok is True
    assert result.ready_seen is True
    assert result.handshake_sent is True
    assert len(result.responses) == 2


def test_run_smoke_command_reports_ready_without_responses(tmp_path: Path) -> None:
    server = tmp_path / "sonar_ready_only.py"
    server.write_text(
        """
from __future__ import annotations

import sys
import time

sys.stderr.write("INFO SonarQube MCP Server - Status: Server ready\\n")
sys.stderr.flush()
time.sleep(10)
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = run_smoke_command(
        [sys.executable, str(server)],
        startup_timeout_seconds=5.0,
        handshake_timeout_seconds=1.0,
    )

    assert result.ok is False
    assert result.ready_seen is True
    assert "did not receive initialize/tools/list" in result.summary


def test_run_smoke_command_rejects_unframed_stdout_preamble_after_ready(tmp_path: Path) -> None:
    server = tmp_path / "sonar_bad_stdout.py"
    server.write_text(
        """
from __future__ import annotations

import sys
import time

sys.stderr.write("INFO SonarQube MCP Server - Status: Server ready\\n")
sys.stderr.flush()
time.sleep(0.1)
sys.stdout.write("oops\\n")
sys.stdout.flush()
time.sleep(0.5)
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = run_smoke_command(
        [sys.executable, str(server)],
        startup_timeout_seconds=5.0,
        handshake_timeout_seconds=2.0,
    )

    assert result.ok is False
    assert "invalid stdout transport output" in result.summary
