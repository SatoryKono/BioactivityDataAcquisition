# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from scripts.ai.mcp.neo4j_memory_mcp_smoke import run_smoke_command

# This module launches nested subprocess transports. Keep it out of parallel
# lanes to avoid Windows runner/socket-pressure setup failures.
pytestmark = [pytest.mark.repo_backed, pytest.mark.serial]


def test_adapter_bridges_framed_client_to_line_delimited_server(tmp_path: Path) -> None:
    server = tmp_path / "line_mcp_server.py"
    server.write_text(
        r"""
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
        sys.stdout.write(json.dumps(response, separators=(",", ":"), sort_keys=True) + "\n")
        sys.stdout.flush()
    elif message.get("method") == "notifications/initialized":
        # Client notification, no response needed
        continue
    elif message.get("method") == "tools/list":
        response = {
            "jsonrpc": "2.0",
            "id": message["id"],
            "result": {
                "tools": [{"name": "search_nodes"}],
            },
        }
        sys.stdout.write(json.dumps(response, separators=(",", ":"), sort_keys=True) + "\n")
        sys.stdout.flush()
        break
    else:
        continue
""".strip()
        + "\n",
        encoding="utf-8",
    )

    adapter = Path("scripts/ai/mcp/neo4j_memory_mcp_adapter.py").resolve()
    result = run_smoke_command(
        [sys.executable, str(adapter), "--", sys.executable, str(server)],
        # Windows CI runners can exhibit higher process startup/jitter near the
        # tail of long suites; this test validates transport bridging semantics.
        timeout_seconds=45.0,
    )

    assert result.ok is True
    assert result.returncode == 0


def test_wrapper_routes_neo4j_memory_through_adapter() -> None:
    wrapper = Path("scripts/ai/mcp/mcp_neo4j_memory_wrapper.sh").read_text(
        encoding="utf-8"
    )

    assert "scripts/ai/mcp/neo4j_memory_mcp_adapter.py" in wrapper
    assert "@knowall-ai/mcp-neo4j-agent-memory@0.2.5" in wrapper
