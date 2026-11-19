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


@pytest.fixture
def private_codex_writer(tmp_path, monkeypatch):
    from copy import deepcopy
    from pathlib import Path
    from scripts.ai.codex import setup_mcp

    home = tmp_path / "private-home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    servers = {
        "memory": {"command": "memory-client", "args": []},
        "prometheus": {"command": "prometheus-client", "args": []},
    }
    monkeypatch.setattr(
        setup_mcp, "_canonical_servers", lambda *args, **kwargs: deepcopy(servers)
    )
    monkeypatch.setattr(
        setup_mcp,
        "_codex_runtime_servers",
        lambda *args, profile="full", **kwargs: deepcopy(
            servers if profile == "full" else {"memory": servers["memory"]}
        ),
    )
    path = home / ".codex/config.toml"
    path.parent.mkdir()
    return setup_mcp, path, tmp_path / "workspace"


@pytest.mark.parametrize("prefix", ["[mcp_servers]\n", ""])
def test_inline_managed_servers_are_replaced_without_losing_custom_entries(
    private_codex_writer, prefix
):
    setup, path, root = private_codex_writer
    name = '"memory"' if prefix else 'mcp_servers."memory"'
    custom = (
        'custom = { command = "private-custom", args = ["--kept"] }'
        if prefix
        else 'mcp_servers.custom = { command = "private-custom", args = ["--kept"] }'
    )
    path.write_text(
        prefix
        + name
        + ' = { command = "old", tool_timeout_sec = 2.75 }\n'
        + custom
        + "\n",
        encoding="utf-8",
    )
    setup._write_codex_config(root, profile="stable")
    text = path.read_text(encoding="utf-8")
    values = tomllib.loads(text)["mcp_servers"]
    assert values["memory"]["command"] == "memory-client"
    assert values["memory"]["tool_timeout_sec"] == 2.75
    assert values["custom"] == {"command": "private-custom", "args": ["--kept"]}
    assert custom in text


def test_profile_round_trip_preserves_inactive_policy_and_not_transport_credentials(
    private_codex_writer,
):
    setup, path, root = private_codex_writer
    path.write_text(
        '[mcp_servers.prometheus]\ncommand = "old"\n'
        "startup_timeout_sec = 3.5\ntool_timeout_sec = 2.75\nenabled = false\n"
        'disabled_tools = ["unsafe_query"]\n'
        'tools = { query = { enabled = false, approval_mode = "ask" } }\n'
        'env = { PRIVATE_CREDENTIAL = "fixture-only-credential" }\n',
        encoding="utf-8",
    )
    original = tomllib.loads(path.read_text(encoding="utf-8"))["mcp_servers"][
        "prometheus"
    ]
    setup._write_codex_config(root, profile="stable")
    stable = path.read_bytes()
    assert "prometheus" not in tomllib.loads(stable.decode())["mcp_servers"]
    assert setup.CODEX_POLICY_ARCHIVE in stable.decode()
    assert "fixture-only-credential" not in stable.decode()
    setup._write_codex_config(root, profile="stable")
    assert path.read_bytes() == stable
    setup._write_codex_config(root, profile="full")
    full = tomllib.loads(path.read_text(encoding="utf-8"))["mcp_servers"]["prometheus"]
    assert {
        field: full[field] for field in setup.CODEX_POLICY_FIELDS if field in original
    } == {
        field: original[field]
        for field in setup.CODEX_POLICY_FIELDS
        if field in original
    }
    assert full["command"] == "prometheus-client" and "env" not in full
    assert setup.CODEX_POLICY_ARCHIVE not in path.read_text(encoding="utf-8")


def test_active_policy_edits_override_the_inactive_archive(private_codex_writer):
    setup, path, root = private_codex_writer
    path.write_text(
        '[mcp_servers.prometheus]\ncommand="old"\ndisabled_tools=["old_policy"]\n',
        encoding="utf-8",
    )
    setup._write_codex_config(root, profile="stable")
    with path.open("a", encoding="utf-8") as stream:
        stream.write(
            '\n[mcp_servers.prometheus]\ncommand="new"\ntool_timeout_sec=1.25\n'
        )
    setup._write_codex_config(root, profile="full")
    current = tomllib.loads(path.read_text(encoding="utf-8"))["mcp_servers"][
        "prometheus"
    ]
    assert current["tool_timeout_sec"] == 1.25 and "disabled_tools" not in current


def test_staged_profile_policy_changes_leave_the_effective_config_untouched(
    private_codex_writer,
):
    setup, path, root = private_codex_writer
    original = '[mcp_servers.prometheus]\ncommand="old"\ndisabled_tools=["write"]\n'
    path.write_text(original, encoding="utf-8")
    staged = setup._write_codex_config(root, profile="stable", stage=True)
    assert path.read_text(encoding="utf-8") == original
    assert setup.CODEX_POLICY_ARCHIVE in staged.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "flag",
    ["--skip-codex", "--skip-codex-config", "--check", "--check-local", "--qodo-only"],
)
def test_staging_rejects_modes_that_cannot_write_a_candidate(
    tmp_path, monkeypatch, flag
):
    from unittest.mock import Mock
    from scripts.ai.codex import setup_mcp

    write = Mock(side_effect=AssertionError("Workspace projections changed"))
    monkeypatch.setattr(setup_mcp, "_write_configs", write)
    output = tmp_path / "uncreated-projection-root"
    with pytest.raises(SystemExit) as error:
        setup_mcp.main(
            [
                "--root",
                str(output),
                "--workspace-root",
                str(tmp_path),
                "--stage-codex-config",
                flag,
            ]
        )
    assert error.value.code == 2
    write.assert_not_called()
    assert not output.exists()


@pytest.mark.parametrize("profile", ["full", "stable"])
def test_shell_readiness_accepts_retained_policies_but_rejects_transport_drift(
    tmp_path, monkeypatch, profile
):
    import sys
    from pathlib import Path
    from scripts.ai.codex import setup_mcp as setup

    home, root = tmp_path / "private-home", tmp_path / "workspace"
    root.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.delenv("BIOETL_CODEX_ROUTES_FILE", raising=False)
    monkeypatch.setenv("CODEX_MCP_PROFILE", profile)
    monkeypatch.setenv("CODEX_MCP_TRANSPORT_MODE", "shared")
    path = home / ".codex/config.toml"
    path.parent.mkdir(parents=True)
    path.write_text(
        '[mcp_servers.prometheus]\nurl="http://127.0.0.1:1/mcp"\ntool_timeout_sec=0.5\n[mcp_servers.memory]\ncommand="old"\ndisabled_tools=["delete_entities"]\n',
        encoding="utf-8",
    )
    setup._write_codex_config(root, profile=profile, transport_mode="shared")
    script = (
        Path(__file__).resolve().parents[3] / "scripts/ai/codex/helper/ensure-mcp.sh"
    )
    shell = script.read_text(encoding="utf-8").split("check_codex_config() {", 1)[1]
    python = (
        "import importlib.util"
        + shell.split("\nimport importlib.util", 1)[1].split("\nPY", 1)[0]
    )
    monkeypatch.setattr(
        sys, "argv", ["-", str(Path(setup.__file__)), str(path), str(root)]
    )
    before = path.read_bytes()
    exec(compile(python, str(script), "exec"), {"__name__": "__main__"})
    assert path.read_bytes() == before
    assert tomllib.loads(before.decode())["mcp_servers"]["memory"][
        "disabled_tools"
    ] == ["delete_entities"]
    text = before.decode()
    memory = setup._codex_runtime_servers(
        root, profile=profile, transport_mode="shared"
    )["memory"]
    assert memory["url"] in text
    path.write_text(
        text.replace(memory["url"], "http://127.0.0.1:1/foreign"), encoding="utf-8"
    )
    drift = path.read_bytes()
    with pytest.raises(SystemExit, match="differs"):
        exec(compile(python, str(script), "exec"), {"__name__": "__main__"})
    assert path.read_bytes() == drift
    path.write_bytes(before + b'\n[mcp_servers.custom]\ncommand="custom"\n')
    exec(compile(python, str(script), "exec"), {"__name__": "__main__"})
    if profile == "stable":
        with path.open("a", encoding="utf-8") as stream:
            stream.write(
                '\n[mcp_servers.prometheus]\ncommand="unexpected"\ntool_timeout_sec=0.5\n'
            )
        extra = path.read_bytes()
        with pytest.raises(SystemExit, match="profile members"):
            exec(compile(python, str(script), "exec"), {"__name__": "__main__"})
        assert path.read_bytes() == extra


def test_root_inline_mcp_table_preserves_custom_data_and_replaces_managed(
    private_codex_writer,
):
    setup, path, root = private_codex_writer
    custom = {
        "command": "custom-📁",
        "args": [r"C:\folder\input"],
        "tools": {"read": {"enabled": False}},
    }
    path.write_text(
        'model = "kept"\nmcp_servers = { memory = { command="old", tool_timeout_sec=0.5 }, custom = '
        + setup._inline_toml_value(custom)
        + "}\n",
        encoding="utf-8",
    )
    setup._write_codex_config(root, profile="stable")
    actual = tomllib.loads(path.read_text(encoding="utf-8"))
    assert actual["model"] == "kept" and actual["mcp_servers"]["custom"] == custom
    assert actual["mcp_servers"]["memory"]["command"] == "memory-client"
    assert actual["mcp_servers"]["memory"]["tool_timeout_sec"] == 0.5


def test_toml_unicode_comment_and_non_bmp_route_survive_atomic_publication(tmp_path):
    from scripts.ai.codex import setup_mcp as setup

    comment = "# kept\u2028inside\u0085comment\r\n"
    servers = {
        "memory": {"command": r"C:\📁\python.exe", "args": ["x\u007fy", "📁\\input"]}
    }
    preserved = setup._strip_managed_mcp_blocks(
        comment + 'model="kept"\r\n', {"memory"}
    )
    assert comment in preserved
    path = tmp_path / "candidate.toml"
    setup._write_user_toml(
        path, preserved + "\n" + setup._render_codex_mcp_toml(servers), before=None
    )
    parsed = tomllib.loads(path.read_text(encoding="utf-8"))
    assert parsed["mcp_servers"]["memory"]["command"] == servers["memory"]["command"]
    assert parsed["mcp_servers"]["memory"]["args"] == servers["memory"]["args"]
