"""Credential delivery is a child-only operation with separate OAuth routing."""

from __future__ import annotations

import hashlib
import json
import tomllib
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.ai.codex import native_session
from scripts.ai.codex.native_session import (
    qualified_binary,
    ref_environment,
    ref_only_overrides,
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


@pytest.fixture
def markdownify_binding(session_binding, tmp_path, monkeypatch):
    root, manifest, _, config = session_binding
    source = b"qualified Markdownify fixture"
    raw = json.dumps(
        {
            "schema": 1,
            "files": {"safe_markdownify.py": hashlib.sha256(source).hexdigest()},
        }
    ).encode()
    versions = tmp_path / "markdownify-versions"
    version = versions / hashlib.sha256(raw).hexdigest()
    version.mkdir(parents=True)
    (version / "owner.json").write_bytes(raw)
    client = version / "safe_markdownify.py"
    client.write_bytes(source)
    monkeypatch.setattr(native_session, "MARKDOWNIFY_VERSIONS", versions)
    entry = {
        "command": str(native_session.BASE_PYTHON),
        "args": ["-I", "-S", "-B", str(client), "client"],
        "startup_timeout_sec": 30,
    }
    binding = tmp_path / "markdownify.json"
    binding.write_text(
        json.dumps(
            {
                "schema": 1,
                "workspace": str(root),
                "git_common": str(root / ".git"),
                "server": "Markdownify-BioETL",
                "entry": entry,
            }
        ),
        encoding="utf-8",
    )
    return root, manifest, config, binding, entry


@pytest.mark.parametrize(
    "policy",
    [
        {"enabled": False},
        {"disabled_tools": ["convert_file"]},
        {"enabled_tools": ["convert_text"]},
        {"tools": {"convert_file": {"enabled": False, "approval_mode": "approve"}}},
        {"startup_timeout_sec": 45, "tool_timeout_sec": 90},
    ],
)
def test_markdownify_session_preserves_policy(markdownify_binding, policy):
    root, manifest, config, binding, entry = markdownify_binding
    previous = {**entry, **policy}
    config["mcp_servers"]["Markdownify-BioETL"] = previous
    before = json.dumps(config, sort_keys=True)
    overrides = session_overrides(config, root, manifest=manifest, markdownify=binding)
    selected = {}
    for value in overrides[1::2]:
        selected.update(tomllib.loads(value)["mcp_servers"])
    assert selected["Markdownify-BioETL"] == previous
    assert json.dumps(config, sort_keys=True) == before
    selected["Markdownify-BioETL"].update({"enabled": True})
    assert json.dumps(config, sort_keys=True) == before


@pytest.mark.parametrize(
    "change",
    [
        {"command": "unqualified"},
        {"args": ["unqualified.py"]},
        {"url": "https://example.invalid/mcp"},
        {"env": {"TOKEN": "fixture"}},
        {"cwd": "/foreign"},
    ],
)
def test_markdownify_policy_does_not_allow_transport_drift(markdownify_binding, change):
    root, manifest, config, binding, entry = markdownify_binding
    config["mcp_servers"]["Markdownify-BioETL"] = {
        **entry,
        "disabled_tools": ["convert_file"],
        **change,
    }
    with pytest.raises(PermissionError, match="unrelated"):
        session_overrides(config, root, manifest=manifest, markdownify=binding)


def test_default_foreign_markdownify_binding_disables_only_that_server(
    session_binding, tmp_path, monkeypatch
):
    root, manifest, _, config = session_binding
    home = tmp_path / "home"
    path = home / ".config/pc-agent/markdownify-bioetl.json"
    path.parent.mkdir(parents=True)
    path.write_text(
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
    monkeypatch.setattr(Path, "home", lambda: home)
    config["mcp_servers"]["Markdownify-BioETL"] = {"command": "unrelated"}
    overrides = session_overrides(config, root, manifest=manifest)
    entries = {}
    for override in overrides[1::2]:
        entries.update(tomllib.loads(override)["mcp_servers"])
    assert entries["memory"]["args"][-1] == "memory"
    assert entries["ast-grep"]["args"][-1] == "ast-grep"
    assert entries["Markdownify-BioETL"] == {"enabled": False}


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


@pytest.mark.parametrize(
    "entry", [{"command": "", "args": []}, {"command": "python", "args": ["client"]}]
)
def test_optional_markdownify_entry_refuses_unqualified_commands(
    session_binding, tmp_path, entry
):
    root, manifest, _, config = session_binding
    source = tmp_path / "markdownify.json"
    source.write_text(
        json.dumps(
            {
                "schema": 1,
                "workspace": str(root),
                "git_common": str(root / ".git"),
                "server": "Markdownify-BioETL",
                "entry": entry,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(PermissionError, match="qualified"):
        session_overrides(config, root, manifest=manifest, markdownify=source)


def test_matching_markdownify_transport_preserves_user_policy(
    session_binding, tmp_path, monkeypatch
):
    root, manifest, _, config = session_binding
    source = tmp_path / "markdownify.json"
    entry = {"command": "qualified-python", "args": ["client"], "tool_timeout_sec": 90}
    source.write_text(
        json.dumps(
            {
                "schema": 1,
                "workspace": str(root),
                "git_common": str(root / ".git"),
                "server": "Markdownify-BioETL",
                "entry": entry,
            }
        ),
        encoding="utf-8",
    )
    checked = []
    monkeypatch.setattr(native_session, "_validate_markdownify_client", checked.append)
    policy = {
        "enabled": False,
        "disabled_tools": ["pdf-to-markdown"],
        "tools": {"html-to-markdown": {"approval_mode": "approve"}},
        "tool_timeout_sec": 30,
    }
    existing = {**entry, **policy}
    config["mcp_servers"]["Markdownify-BioETL"] = existing
    result = session_overrides(config, root, manifest=manifest, markdownify=source)
    overrides = {}
    for item in result[1::2]:
        overrides.update(tomllib.loads(item)["mcp_servers"])
    assert overrides["Markdownify-BioETL"] == existing
    assert checked == [entry]
    existing["cwd"] = str(root)
    with pytest.raises(PermissionError, match="unrelated Markdownify"):
        session_overrides(config, root, manifest=manifest, markdownify=source)


def test_native_operational_cli_returns_redacted_failure(monkeypatch, capsys):
    def fail():
        raise PermissionError("private workspace diagnostic")

    monkeypatch.setattr(native_session, "workspace", fail)
    assert (
        native_session.main(["--executable", "unused", "--sha256", "a" * 64, "--check"])
        == 64
    )
    assert "private workspace diagnostic" not in capsys.readouterr().err


@pytest.mark.parametrize(
    "change", ["relative", "foreign", "interpreter", "drift", "manifest"]
)
def test_native_selector_requires_the_physical_pinned_installation(
    session_binding, tmp_path, monkeypatch, change
):
    root, manifest, data, config = session_binding
    entry = data["entries"]["memory"]
    if change == "relative":
        entry["args"][3] = "session_client.py"
    elif change == "foreign":
        foreign = tmp_path / "session_client.py"
        foreign.write_bytes(b"# same basename, unrelated script\n")
        entry["args"][3] = str(foreign)
    elif change == "interpreter":
        entry["command"] = "python"
    elif change == "drift":
        Path(entry["args"][3]).write_bytes(b"# changed after qualification\n")
    else:
        Path(entry["args"][3]).with_name("dispatcher.json").unlink()
    manifest.write_text(json.dumps(data), encoding="utf-8")
    cwd = root / "docs"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    with pytest.raises(PermissionError, match="selector|dispatcher"):
        session_overrides(
            config, root, manifest=manifest, markdownify=tmp_path / "absent.json"
        )
    assert Path.cwd() == cwd


@pytest.fixture
def ref_launch(session_binding, monkeypatch, tmp_path):
    import dotenv

    root, manifest, _, config = session_binding
    config = deepcopy(config)
    config["mcp_servers"]["ref"] = {
        "url": native_session.REF_URL,
        "env_http_headers": {"x-ref-api-key": "REF_TOOL_API_KEY"},
        "enabled": False,
    }
    config["mcp_servers"]["Markdownify-BioETL"] = {
        "command": "unrelated-installed-client",
        "enabled": True,
    }
    config["mcp_servers"]["custom.name"] = {
        "command": "unrelated-custom-client",
        "enabled": True,
    }
    home = tmp_path / "ref-home"
    config_path = home / ".codex/config.toml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        "mcp_servers = " + native_session.toml_value(config["mcp_servers"]) + "\n",
        encoding="utf-8",
    )
    binary = home / "AppData/Local/OpenAI/Codex/bin/qualified/codex.exe"
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b"qualified Ref-session executable fixture")
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.chdir(root)
    monkeypatch.setattr(native_session, "workspace", lambda: (root, root))
    monkeypatch.setenv("BIOETL_CODEX_ROUTES_FILE", str(manifest))
    physical = native_session.physical
    # No .env fixture is created; dotenv data is supplied only in memory.
    monkeypatch.setattr(
        native_session,
        "physical",
        lambda path: path if path == root / ".env" else physical(path),
    )
    monkeypatch.setattr(
        dotenv, "dotenv_values", lambda path: {"REF_TOOL_API_KEY": "fixture-ref-key"}
    )
    calls = []

    def call(argv, *, cwd, env, **_kwargs):
        calls.append({"argv": argv, "cwd": cwd, "ref_key": env["REF_TOOL_API_KEY"]})
        return 0

    monkeypatch.setattr(native_session.subprocess, "call", call)
    return {
        "root": root,
        "home": home,
        "config": config,
        "config_path": config_path,
        "calls": calls,
        "argv": [
            "--executable",
            str(binary),
            "--sha256",
            hashlib.sha256(binary.read_bytes()).hexdigest(),
            "--auth",
            "api-key",
        ],
    }


def test_ref_only_disables_other_servers_without_changing_settings():
    config = {
        "mcp_servers": {
            "ref": {
                "url": native_session.REF_URL,
                "enabled": False,
                "tools": {"ref_read_url": {"approval_mode": "approve"}},
            },
            "memory": {"command": "unrelated", "enabled": True},
            "Markdownify-BioETL": {"command": "unrelated", "enabled": False},
            "custom.name": {"command": "unrelated", "enabled": True},
            'custom."\U0001f9ea"': {"command": "unrelated", "enabled": True},
        }
    }
    original = deepcopy(config)

    overrides = ref_only_overrides(config)

    effective = deepcopy(config)
    assert len(overrides) == 2
    assert overrides[0] == "--config"
    assert overrides[1].startswith("mcp_servers=")
    entries = tomllib.loads(overrides[1])["mcp_servers"]
    assert entries.keys() == original["mcp_servers"].keys()
    for name, changes in entries.items():
        assert set(changes) == {"enabled"}
        effective["mcp_servers"][name].update(changes)
    assert config == original
    assert {
        name for name, entry in effective["mcp_servers"].items() if entry["enabled"]
    } == {"ref"}
    assert (
        effective["mcp_servers"]["ref"]["tools"]
        == original["mcp_servers"]["ref"]["tools"]
    )


@pytest.mark.parametrize(("name", "entry"), [("", {}), (1, {}), ("custom.name", True)])
def test_ref_only_rejects_invalid_server_entries(name, entry):
    config = {"mcp_servers": {"ref": {}, name: entry}}
    with pytest.raises(PermissionError, match="safe configured server names"):
        ref_only_overrides(config)


@pytest.mark.parametrize("binding_state", ["foreign", "unavailable"])
def test_ref_only_does_not_load_unrelated_markdownify_binding(
    ref_launch, monkeypatch, binding_state
):
    binding = ref_launch["home"] / ".config/pc-agent/markdownify-bioetl.json"
    binding.parent.mkdir(parents=True)
    binding.write_text(
        json.dumps(
            {
                "schema": 1,
                "workspace": str(ref_launch["home"] / "foreign"),
                "git_common": str(ref_launch["root"] / ".git"),
                "server": "Markdownify-BioETL",
            }
        ),
        encoding="utf-8",
    )
    read_bytes = Path.read_bytes
    if binding_state == "unavailable":

        def read(path):
            if path == binding:
                raise PermissionError("Unrelated Markdownify binding unavailable")
            return read_bytes(path)

        monkeypatch.setattr(Path, "read_bytes", read)
    scoped_calls = []
    session_overrides_original = native_session.session_overrides

    def scoped(*args, **kwargs):
        scoped_calls.append(True)
        return session_overrides_original(*args, **kwargs)

    monkeypatch.setattr(native_session, "session_overrides", scoped)
    original_config = ref_launch["config_path"].read_bytes()
    if binding_state == "unavailable":
        with pytest.raises(PermissionError, match="unavailable"):
            native_session._run(ref_launch["argv"])
    else:
        assert native_session._run(ref_launch["argv"]) == 0
        [ordinary_call] = ref_launch["calls"]
        assert (
            'mcp_servers.Markdownify-BioETL={"enabled"=false}' in ordinary_call["argv"]
        )
        ref_launch["calls"].clear()
    assert len(scoped_calls) == 1
    assert not ref_launch["calls"]

    assert native_session.main([*ref_launch["argv"], "--ref-only"]) == 0

    assert len(scoped_calls) == 1
    assert len(ref_launch["calls"]) == 1
    call = ref_launch["calls"][0]
    assert call["cwd"] == ref_launch["root"]
    assert call["argv"][1:3] == ["--cd", str(ref_launch["root"])]
    assert call["ref_key"] == "fixture-ref-key"
    assert "fixture-ref-key" not in " ".join(call["argv"])
    _, _, _, first_flag, selection, second_flag, pin = call["argv"]
    assert (first_flag, second_flag) == ("--config", "--config")
    original_ref = tomllib.loads(original_config.decode())["mcp_servers"]["ref"]
    assert original_ref["enabled"] is False
    assert tomllib.loads(pin)["mcp_servers"]["ref"] == {**original_ref, "enabled": True}
    entries = tomllib.loads(selection)["mcp_servers"]
    assert {name: entry["enabled"] for name, entry in entries.items()} == {
        "memory": False,
        "ast-grep": False,
        "ref": True,
        "Markdownify-BioETL": False,
        "custom.name": False,
    }
    assert ref_launch["config_path"].read_bytes() == original_config


def test_ref_only_check_reports_selection_without_starting_client(ref_launch, capsys):
    original_config = ref_launch["config_path"].read_bytes()

    assert native_session.main([*ref_launch["argv"], "--ref-only", "--check"]) == 0

    output = capsys.readouterr().out
    report = json.loads(output)
    assert report["ref_only"] is True
    assert report["selected_servers"] == ["ref"]
    assert report["spawned"] is False
    assert report["native_request"] == "NOT_TESTED"
    assert report["root_credential_present"] is True
    assert "fixture-ref-key" not in output
    assert hashlib.sha256(b"fixture-ref-key").hexdigest() not in output
    assert not ref_launch["calls"]
    assert ref_launch["config_path"].read_bytes() == original_config


@pytest.mark.parametrize("change", ["missing", "oauth", "query", "literal-header"])
def test_ref_only_keeps_authorization_guards(ref_launch, monkeypatch, change):
    import dotenv

    argv = [*ref_launch["argv"], "--ref-only"]
    if change == "missing":
        monkeypatch.setattr(dotenv, "dotenv_values", lambda path: {})
    elif change == "oauth":
        argv[argv.index("--auth") + 1] = "oauth"
    else:
        config = deepcopy(ref_launch["config"])
        ref = config["mcp_servers"]["ref"]
        if change == "query":
            ref["url"] += "?apiKey=fixture-only"
        else:
            ref["http_headers"] = {"x-ref-api-key": "fixture-only"}
        ref_launch["config_path"].write_text(
            "mcp_servers = " + native_session.toml_value(config["mcp_servers"]) + "\n",
            encoding="utf-8",
        )

    with pytest.raises(PermissionError, match="absent|separate"):
        native_session._run(argv)
    assert not ref_launch["calls"]


def test_ref_only_still_requires_the_qualified_executable(ref_launch):
    argv = [*ref_launch["argv"], "--ref-only"]
    argv[argv.index("--sha256") + 1] = "0" * 64
    with pytest.raises(PermissionError, match="executable drift"):
        native_session._run(argv)
    assert native_session.main(argv) == 64
    assert not ref_launch["calls"]


def test_ref_only_cannot_enable_the_acceptance_graph(ref_launch, capsys):
    with pytest.raises(SystemExit) as caught:
        native_session.main([*ref_launch["argv"], "--ref-only", "--acceptance"])
    assert caught.value.code == 2
    assert "not allowed with argument" in capsys.readouterr().err
    assert not ref_launch["calls"]


def test_default_foreign_markdownify_binding_keeps_memory_and_ast(
    session_binding, tmp_path, monkeypatch
):
    root, manifest, _, config = session_binding
    home = tmp_path / "client-home"
    source = home / ".config/pc-agent/markdownify-bioetl.json"
    source.parent.mkdir(parents=True)
    source.write_text(
        json.dumps(
            {
                "schema": 1,
                "workspace": str(tmp_path / "foreign"),
                "server": "Markdownify-BioETL",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(Path, "home", lambda: home)
    args = session_overrides(config, root, manifest=manifest)
    assert len(args) == 4
    assert args[1].startswith("mcp_servers.memory=")
    assert args[3].startswith("mcp_servers.ast-grep=")


def test_native_workspace_does_not_skip_a_dangling_nearest_git_marker(
    tmp_path, monkeypatch
):
    from types import SimpleNamespace

    outer, inner = tmp_path / "outer", tmp_path / "outer/nested"
    inner.mkdir(parents=True)
    (outer / ".git").mkdir()
    original = native_session.os.path.lexists
    monkeypatch.setattr(
        native_session.os.path,
        "lexists",
        lambda path: True if Path(path) == inner / ".git" else original(path),
    )
    monkeypatch.setattr(Path, "cwd", lambda: inner)

    def validate(path):
        assert path == inner
        raise PermissionError("Broken nearest marker")

    roots = SimpleNamespace(physical_root=validate)
    monkeypatch.setattr(
        native_session.importlib.util,
        "spec_from_file_location",
        lambda *args: SimpleNamespace(
            loader=SimpleNamespace(exec_module=lambda _: None)
        ),
    )
    monkeypatch.setattr(
        native_session.importlib.util, "module_from_spec", lambda _: roots
    )
    with pytest.raises(PermissionError, match="nearest marker"):
        native_session.workspace()


@pytest.mark.parametrize(
    "policy",
    [
        {"enabled": False},
        {"disabled_tools": ["pdf-to-markdown"]},
        {"enabled_tools": ["get-markdown-file"]},
        {"tools": {"get-markdown-file": {"approval_mode": "approve"}}},
        {"startup_timeout_sec": 0.75, "tool_timeout_sec": 2.25},
    ],
)
def test_matching_markdownify_transport_preserves_existing_policies(
    session_binding, tmp_path, monkeypatch, policy
):
    from copy import deepcopy

    root, manifest, _, config = session_binding
    entry = {
        "command": "qualified-fixture",
        "args": ["client"],
        "startup_timeout_sec": 60,
    }
    config["mcp_servers"]["Markdownify-BioETL"] = {**entry, **policy}
    original = deepcopy(config)
    source = tmp_path / "markdownify.json"
    source.write_text(
        json.dumps(
            {
                "schema": 1,
                "server": "Markdownify-BioETL",
                "workspace": str(root),
                "git_common": str(root / ".git"),
                "entry": entry,
            }
        ),
        encoding="utf-8",
    )
    validated = []
    monkeypatch.setattr(
        native_session,
        "_validate_markdownify_client",
        lambda value: validated.append(value),
    )
    entries = {}
    for value in session_overrides(config, root, manifest=manifest, markdownify=source)[
        1::2
    ]:
        entries.update(tomllib.loads(value)["mcp_servers"])
    assert entries["Markdownify-BioETL"] == {**entry, **policy}
    assert validated == [entry] and config == original
    config["mcp_servers"]["Markdownify-BioETL"]["command"] = "foreign"
    with pytest.raises(PermissionError, match="unrelated"):
        session_overrides(config, root, manifest=manifest, markdownify=source)


def test_route_validation_uses_the_original_snapshot_during_aba_swap(
    session_binding, tmp_path, monkeypatch
):
    from scripts.ai.codex import local_mcp_routes as routes

    root, manifest, data, config = session_binding
    original = manifest.read_bytes()
    original_apply = routes.apply_local_routes

    def swapped(servers, workspace, *, manifest, snapshot):
        assert snapshot == original
        changed = json.loads(original)
        changed["entries"]["memory"]["command"] = "unqualified-ABA"
        manifest.write_text(json.dumps(changed), encoding="utf-8")
        try:
            return original_apply(
                servers, workspace, manifest=manifest, snapshot=snapshot
            )
        finally:
            manifest.write_bytes(original)

    monkeypatch.setattr(routes, "apply_local_routes", swapped)
    entries = {}
    for value in session_overrides(
        config, root, manifest=manifest, markdownify=tmp_path / "absent.json"
    )[1::2]:
        entries.update(tomllib.loads(value)["mcp_servers"])
    assert entries["memory"]["command"] == data["entries"]["memory"]["command"]


@pytest.mark.parametrize(
    "policy",
    [
        {"disabled_tools": ["delete_entities"]},
        {"enabled_tools": ["read_graph"]},
        {"tools": {"read_graph": {"approval_mode": "approve"}}},
        {"enabled": False},
    ],
)
def test_acceptance_override_retains_its_own_policy(session_binding, tmp_path, policy):
    root, manifest, data, config = session_binding
    config["mcp_servers"]["memory-acceptance"] = {"command": "old", **policy}
    original = json.dumps(config, sort_keys=True)
    entries = {}
    for value in session_overrides(
        config,
        root,
        manifest=manifest,
        markdownify=tmp_path / "absent.json",
        acceptance=True,
    )[1::2]:
        entries.update(tomllib.loads(value)["mcp_servers"])
    actual = entries["memory-acceptance"]
    assert actual["args"][-1] == "memory-acceptance"
    for key, value in policy.items():
        assert actual[key] == value
    assert ("tools" in actual) == ("tools" in policy)
    assert json.dumps(config, sort_keys=True) == original


@pytest.mark.parametrize("foreign", [False, True])
def test_ref_validation_and_child_use_the_same_codex_home(
    session_binding, tmp_path, monkeypatch, foreign
):
    from unittest.mock import Mock
    from scripts.ai.codex.setup_mcp import _render_codex_mcp_toml

    root, manifest, _, config = session_binding
    home, alternate = tmp_path / "home", tmp_path / "alternate"
    (home / ".codex").mkdir(parents=True)
    alternate.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.setenv("CODEX_HOME", str(alternate))
    monkeypatch.setenv("BIOETL_CODEX_ROUTES_FILE", str(manifest))
    monkeypatch.chdir(root)
    monkeypatch.setattr(native_session, "workspace", lambda: (root, root))
    servers = {
        "memory": {"command": "old-memory"},
        "ast-grep": {"command": "old-ast"},
        "ref": {"url": native_session.REF_URL},
    }
    (home / ".codex/config.toml").write_text(
        _render_codex_mcp_toml(servers), encoding="utf-8"
    )
    if foreign:
        servers["ref"]["url"] = "https://foreign.invalid/mcp"
    (alternate / "config.toml").write_text(
        _render_codex_mcp_toml(servers), encoding="utf-8"
    )
    binary = home / "AppData/Local/OpenAI/Codex/bin/qualified/codex.exe"
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b"qualified native fixture")
    call = Mock(return_value=0)
    monkeypatch.setattr(native_session.subprocess, "call", call)
    args = [
        "--executable",
        str(binary),
        "--sha256",
        hashlib.sha256(binary.read_bytes()).hexdigest(),
        "--auth",
        "oauth",
    ]
    if foreign:
        with pytest.raises(PermissionError, match="separate"):
            native_session._run(args)
        call.assert_not_called()
    else:
        assert native_session._run(args) == 0
        assert call.call_args.kwargs["env"]["CODEX_HOME"] == str(alternate)
        settings = {}
        argv = call.call_args.args[0]
        for index, item in enumerate(argv[:-1]):
            if item == "--config":
                settings.update(tomllib.loads(argv[index + 1])["mcp_servers"])
        assert settings["ref"] == {"url": native_session.REF_URL}
