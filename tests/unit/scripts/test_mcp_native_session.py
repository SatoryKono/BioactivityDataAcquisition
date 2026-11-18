"""Credential delivery is a child-only operation with separate OAuth routing."""

import hashlib
import json
import tomllib
from pathlib import Path

import pytest

from scripts.ai.codex import native_session
from scripts.ai.codex.native_session import (
    qualified_binary,
    ref_environment,
    session_overrides,
    validate_ref,
)

pytestmark = pytest.mark.unit


def test_only_ref_value_is_added_without_mutating_parent():
    parent = {"PATH": "fixture-path", "REF_TOOL_API_KEY": "old-fixture"}
    values = {"REF_TOOL_API_KEY": "fixture-only", "GITHUB_TOKEN": "unrelated-fixture"}
    result = ref_environment(parent, values, "api-key")
    assert result == {"PATH": "fixture-path", "REF_TOOL_API_KEY": "fixture-only"}
    assert parent["REF_TOOL_API_KEY"] == "old-fixture"
    assert "GITHUB_TOKEN" not in result


def test_oauth_never_inherits_an_api_key():
    assert ref_environment({"REF_TOOL_API_KEY": "fixture-only"}, {}, "oauth") == {}
    with pytest.raises(PermissionError, match="absent"):
        ref_environment({}, {}, "api-key")


def test_authorization_branches_cannot_be_mixed():
    key_route = {
        "mcp_servers": {
            "ref": {
                "url": "https://api.ref.tools/mcp",
                "env_http_headers": {"x-ref-api-key": "REF_TOOL_API_KEY"},
            }
        }
    }
    validate_ref(key_route, "api-key")
    with pytest.raises(PermissionError, match="separate"):
        validate_ref(key_route, "oauth")
    with pytest.raises(PermissionError, match="separate"):
        validate_ref(
            {
                "mcp_servers": {
                    "ref": {"url": "https://api.ref.tools/mcp?apiKey=fixture-only"}
                }
            },
            "api-key",
        )


def test_only_exact_qualified_app_binary_is_selected(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    binary = tmp_path / "AppData/Local/OpenAI/Codex/bin/qualified/codex.exe"
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b"qualified executable fixture")
    expected = hashlib.sha256(binary.read_bytes()).hexdigest()
    assert qualified_binary(binary, expected) == binary
    binary.write_bytes(b"changed executable fixture")
    with pytest.raises(PermissionError, match="drift"):
        qualified_binary(binary, expected)
    foreign = tmp_path / "foreign/codex.exe"
    foreign.parent.mkdir()
    foreign.write_bytes(b"qualified executable fixture")
    with pytest.raises(PermissionError, match="app-owned"):
        qualified_binary(foreign, expected)


@pytest.fixture
def session_binding(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    (root / ".git").mkdir(parents=True)
    manifest = tmp_path / "routes.json"
    python = tmp_path / "python.exe"
    python.write_bytes(b"qualified interpreter fixture")
    source = b"qualified dispatcher fixture"
    snapshot = {
        "schema": 1,
        "files": {"session_client.py": hashlib.sha256(source).hexdigest()},
        "host_pins": {str(python): hashlib.sha256(python.read_bytes()).hexdigest()},
    }
    raw = json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
    versions = tmp_path / "selectors"
    directory = versions / hashlib.sha256(raw).hexdigest()
    directory.mkdir(parents=True)
    (directory / "dispatcher.json").write_bytes(raw)
    selector = directory / "session_client.py"
    selector.write_bytes(source)
    monkeypatch.setattr(native_session, "BASE_PYTHON", python)
    monkeypatch.setattr(native_session, "SESSION_VERSIONS", versions)
    data = {
        "schema": 1,
        "git_common": str(root / ".git"),
        "entries": {
            name: {
                "command": str(python),
                "args": ["-I", "-S", "-B", str(selector), name],
            }
            for name in ("memory", "ast-grep")
        },
    }
    manifest.write_text(json.dumps(data), encoding="utf-8")
    config = {
        "mcp_servers": {
            "memory": {
                "url": "http://127.0.0.1:1/mcp",
                "tools": {"read_graph": {"approval_mode": "approve"}},
            },
            "ast-grep": {"url": "http://127.0.0.1:2/mcp"},
        }
    }
    return root, manifest, data, config


def test_session_overrides_replace_transport_and_preserve_tool_approval(
    session_binding, tmp_path
):
    root, manifest, _, config = session_binding
    args = session_overrides(
        config,
        root,
        manifest=manifest,
        markdownify=tmp_path / "absent.json",
        acceptance=True,
    )
    entries = {}
    for value in args[1::2]:
        entries.update(tomllib.loads(value)["mcp_servers"])
    assert "url" not in entries["memory"]
    assert entries["memory"]["tools"] == config["mcp_servers"]["memory"]["tools"]
    assert entries["memory-acceptance"]["args"][-1] == "memory-acceptance"
    assert config["mcp_servers"]["memory"]["url"] == "http://127.0.0.1:1/mcp"


def test_explicit_pinned_root_route_is_not_a_session_binding(session_binding, tmp_path):
    root, manifest, data, config = session_binding
    data["entries"]["memory"]["args"] = ["scoped.py", "--workspace", str(root)]
    manifest.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(PermissionError, match="inherited-cwd"):
        session_overrides(
            config, root, manifest=manifest, markdownify=tmp_path / "absent.json"
        )


def test_markdownify_source_cannot_redirect_a_foreign_workspace(
    session_binding, tmp_path
):
    root, manifest, _, config = session_binding
    custom = tmp_path / "markdownify.json"
    custom.write_text(
        json.dumps(
            {
                "schema": 1,
                "workspace": str(tmp_path / "foreign"),
                "git_common": str(root / ".git"),
                "server": "Markdownify-BioETL",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(PermissionError, match="workspace"):
        session_overrides(config, root, manifest=manifest, markdownify=custom)


def test_session_uses_explicit_environment_manifest(
    session_binding, monkeypatch, tmp_path
):
    root, manifest, _, config = session_binding
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "empty-home")
    monkeypatch.setenv("BIOETL_CODEX_ROUTES_FILE", str(manifest))

    overrides = session_overrides(config, root)

    entries = {}
    for value in overrides[1::2]:
        entries.update(tomllib.loads(value)["mcp_servers"])
    assert entries["memory"]["args"][-1] == "memory"
    assert entries["ast-grep"]["args"][-1] == "ast-grep"


def test_child_keeps_validated_session_subdirectory(
    session_binding, monkeypatch, tmp_path
):
    root, manifest, _, _ = session_binding
    cwd = root / "docs"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(native_session, "workspace", lambda: (root, root))
    home = tmp_path / "home"
    cfg = home / ".codex/config.toml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(
        '[mcp_servers.ref]\nurl = "https://api.ref.tools/mcp"\n'
        '[mcp_servers.memory]\ncommand = "old-memory"\n'
        '[mcp_servers.ast-grep]\ncommand = "old-ast"\n'.replace("\\\n", "\n"),
        encoding="utf-8",
    )
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.setenv("BIOETL_CODEX_ROUTES_FILE", str(manifest))
    binary = home / "AppData/Local/OpenAI/Codex/bin/qualified/codex.exe"
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b"qualified executable fixture")
    seen = []

    def call(args, *, cwd, **_kwargs):
        seen.append((args, cwd))
        return 0

    monkeypatch.setattr(native_session.subprocess, "call", call)
    assert (
        native_session.main(
            [
                "--executable",
                str(binary),
                "--sha256",
                hashlib.sha256(binary.read_bytes()).hexdigest(),
                "--auth",
                "oauth",
            ]
        )
        == 0
    )
    assert len(seen) == 1
    assert seen[0][0][:3] == [str(binary), "--cd", str(cwd)]
    assert seen[0][1] == cwd


@pytest.mark.parametrize("change", ["relative", "interpreter", "source"])
def test_session_refuses_unqualified_selector_before_launch(
    session_binding, tmp_path, change
):
    root, manifest, data, config = session_binding
    entry = data["entries"]["memory"]
    if change == "relative":
        entry["args"][3] = "session_client.py"
    elif change == "interpreter":
        entry["command"] = "python"
    else:
        Path(entry["args"][3]).write_bytes(b"changed dispatcher source")
    manifest.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(PermissionError, match="qualified|source changed"):
        session_overrides(
            config, root, manifest=manifest, markdownify=tmp_path / "absent.json"
        )
