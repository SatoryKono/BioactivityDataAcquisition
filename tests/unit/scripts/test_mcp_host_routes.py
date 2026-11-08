"""Machine-local transport routing must not broaden profiles or overwrite client policy."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ops.runtime.mcp.host_routes import load_host_routes, merge_host_routes


def make_config(tmp_path: Path, root: Path, entries: dict) -> Path:
    source = tmp_path / "outside-checkout.json"
    source.write_text(
        json.dumps({"workspaces": [{"roots": [str(root)], "entries": entries}]}),
        encoding="utf-8",
    )
    return source


def test_external_input_survives_absent_checkout_marker(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    entry = {"command": "node", "args": ["adapter", "context7"]}
    source = make_config(tmp_path, root, {"context7": entry})
    marker = tmp_path / "home-marker.json"
    marker.write_text(json.dumps({"source": str(source)}), encoding="utf-8")
    assert load_host_routes(root, marker=marker) == {"context7": entry}
    assert load_host_routes(tmp_path / "other-workspace", marker=marker) == {}


def test_host_input_never_enables_unselected_service_or_loses_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    marker = make_config(
        tmp_path,
        root,
        {
            "context7": {"command": "node", "args": ["adapter"]},
            "brave-search": {"command": "node", "args": ["brave"]},
        },
    )
    monkeypatch.setenv("PC_AGENT_MCP_ROUTES_FILE", str(marker))
    servers = {
        "context7": {
            "url": "http://old",
            "disabled": True,
            "autoApprove": [],
            "tool_timeout_sec": 71,
        }
    }
    projected = merge_host_routes(servers, root, allowed={"context7", "brave-search"})
    assert set(projected) == {"context7"}
    assert projected["context7"] == {
        "command": "node",
        "args": ["adapter"],
        "disabled": True,
        "autoApprove": [],
        "tool_timeout_sec": 71,
    }
    assert servers["context7"]["url"] == "http://old"


def test_host_input_rejects_unknown_service(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "workspace"
    marker = make_config(
        tmp_path, root, {"not-approved": {"command": "node", "args": []}}
    )
    monkeypatch.setenv("PC_AGENT_MCP_ROUTES_FILE", str(marker))
    with pytest.raises(ValueError, match="outside the shared"):
        merge_host_routes({}, root, allowed={"context7"})


def test_host_input_rejects_credentials_in_routes(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    marker = make_config(
        tmp_path,
        root,
        {"context7": {"command": "node", "args": [], "env": {"TOKEN": "fixture"}}},
    )
    with pytest.raises(ValueError, match="credentials"):
        load_host_routes(root, marker=marker)


def test_host_input_rejects_indirection_loop(tmp_path: Path) -> None:
    marker = tmp_path / "loop.json"
    marker.write_text(json.dumps({"source": str(marker)}), encoding="utf-8")
    with pytest.raises(ValueError, match="cycle"):
        load_host_routes(tmp_path, marker=marker)
