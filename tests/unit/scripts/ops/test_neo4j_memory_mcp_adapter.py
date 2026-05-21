from __future__ import annotations

import sys
from pathlib import Path

import pytest

from scripts.ai.mcp.neo4j_memory_mcp_smoke import run_smoke_command

pytestmark = [pytest.mark.memory, pytest.mark.repo_backed]


def test_adapter_bridges_framed_client_to_line_delimited_server(tmp_path: Path) -> None:
    server = tmp_path / "line_mcp_server.py"
    server.write_text(
        """
from __future__ import annotations

import json
import sys


for raw_line in sys.stdin:
    message = json.loads(raw_line)
    if message.get("method") == "initialize":
        response = {
            "jsonrpc": "2.0",
            "id": message["id"],
            "result": {
                "protocolVersion": message["params"]["protocolVersion"],
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "line-server", "version": "1.0"},
            },
        }
    elif message.get("method") == "tools/list":
        response = {
            "jsonrpc": "2.0",
            "id": message["id"],
            "result": {
                "tools": [{"name": "search_nodes"}],
            },
        }
        sys.stdout.write(json.dumps(response, separators=(",", ":"), sort_keys=True) + "\\n")
        sys.stdout.flush()
        break
    else:
        continue
    sys.stdout.write(json.dumps(response, separators=(",", ":"), sort_keys=True) + "\\n")
    sys.stdout.flush()
""".strip()
        + "\n",
        encoding="utf-8",
    )

    adapter = Path("scripts/ai/mcp/neo4j_memory_mcp_adapter.py").resolve()
    result = run_smoke_command(
        [sys.executable, str(adapter), "--", sys.executable, str(server)],
        # Windows CI runners can exhibit higher process startup/jitter near the
        # tail of long suites; this test validates transport bridging semantics.
        timeout_seconds=15.0,
    )

    assert result.ok is True
    assert result.returncode == 0


def test_wrapper_routes_neo4j_memory_through_adapter() -> None:
    wrapper = Path("scripts/ai/mcp/mcp_neo4j_memory_wrapper.sh").read_text(
        encoding="utf-8"
    )

    assert "scripts/ai/mcp/neo4j_memory_mcp_adapter.py" in wrapper
    assert "@knowall-ai/mcp-neo4j-agent-memory@0.2.5" in wrapper
