"""Codex stdio rendering preserves an explicitly supplied working directory."""

from __future__ import annotations

import tomllib

import pytest

from scripts.ai.codex.setup_mcp import _render_codex_mcp_toml

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("cwd", [None, "../workspace", "D:/registered/workspace"])
def test_stdio_transport_round_trip_preserves_optional_cwd(cwd: str | None) -> None:
    server = {
        "command": "python.exe",
        "args": ["-B", "fixture.py"],
        "startup_timeout_sec": 90,
    }
    if cwd is not None:
        server["cwd"] = cwd

    parsed = tomllib.loads(_render_codex_mcp_toml({"memory": server}))

    assert parsed["mcp_servers"]["memory"] == server


def test_http_transport_does_not_gain_a_stdio_working_directory() -> None:
    rendered = _render_codex_mcp_toml({"fixture": {"url": "http://127.0.0.1:1234/mcp"}})
    assert tomllib.loads(rendered)["mcp_servers"]["fixture"] == {
        "url": "http://127.0.0.1:1234/mcp"
    }
