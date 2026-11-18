"""Native route synchronization must preserve isolation and user-owned settings."""

import json
from pathlib import Path

import pytest

from scripts.ai.codex import setup_mcp
from scripts.ai.codex.local_mcp_routes import apply_local_routes
from scripts.ai.mcp.session_client import session_root

pytestmark = pytest.mark.unit


@pytest.fixture
def routes(tmp_path):
    root = tmp_path / "repo"
    (root / ".git").mkdir(parents=True)
    path = tmp_path / "routes.json"
    data = {
        "schema": 1,
        "git_common": str(root / ".git"),
        "entries": {
            "memory": {"command": "python", "args": ["session_client.py", "memory"]}
        },
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    return root, path, data


def test_sync_preserves_custom_native_route_and_user_preferences(
    routes, monkeypatch, tmp_path
):
    root, path, _ = routes
    monkeypatch.setenv("BIOETL_CODEX_ROUTES_FILE", str(path))
    home = tmp_path / "home"
    (home / ".codex").mkdir(parents=True)
    monkeypatch.setattr(Path, "home", lambda: home)
    config = home / ".codex/config.toml"
    custom = (
        'model = "user-model"\n[mcp_servers.custom]\ncommand = "custom"\n'
        '[mcp_servers.memory]\ncommand = "old"\nenabled_tools = ["read_graph"]\n'
        '[mcp_servers.memory.tools.read_graph]\napproval_mode = "approve"\n'
    )
    config.write_text(custom, encoding="utf-8")
    setup_mcp._write_codex_config(root, profile="stable", transport_mode="shared")
    first = config.read_bytes()
    setup_mcp._write_codex_config(root, profile="stable", transport_mode="shared")
    assert config.read_bytes() == first
    text = first.decode()
    assert 'model = "user-model"' in text and "[mcp_servers.custom]" in text
    assert text.count("[mcp_servers.memory]") == 1
    assert "session_client.py" in text
    assert 'enabled_tools = ["read_graph"]' in text
    assert 'approval_mode = "approve"' in text
    assert (
        "cwd =" not in text.split("[mcp_servers.memory]")[1].split("[mcp_servers.")[0]
    )


@pytest.mark.parametrize(
    "field,value",
    [("cwd", "foreign"), ("env", {}), ("headers", {}), ("url", "https://foreign")],
)
def test_rejects_context_pins_and_credential_channels(routes, field, value):
    root, path, data = routes
    data["entries"]["memory"][field] = value
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="credential-free"):
        apply_local_routes({"memory": {}}, root, manifest=path)


def test_foreign_repository_never_receives_binding(routes, tmp_path):
    _, path, _ = routes
    foreign = tmp_path / "foreign"
    (foreign / ".git").mkdir(parents=True)
    with pytest.raises(ValueError, match="another repository"):
        apply_local_routes({"memory": {}}, foreign, manifest=path)


def test_ref_cannot_be_overridden_by_stdio_manifest(routes):
    root, path, data = routes
    data["entries"]["ref"] = data["entries"].pop("memory")
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="credential-free"):
        apply_local_routes({"ref": {}}, root, manifest=path)


def test_nearest_nested_repository_is_validated_instead_of_parent(routes):
    root, _, _ = routes
    nested = root / "nested"
    (nested / ".git").mkdir(parents=True)
    source = nested / "src"
    source.mkdir()

    def validator(candidate):
        assert candidate == nested
        raise PermissionError("Foreign nested repo")

    with pytest.raises(PermissionError, match="nested"):
        session_root(source, validator)


def test_session_subdirectory_preserves_actual_root(routes):
    root, _, _ = routes
    source = root / "src"
    source.mkdir()
    assert session_root(source, lambda candidate: candidate) == root


def test_explicit_missing_manifest_is_not_a_fallback(tmp_path, monkeypatch):
    monkeypatch.setenv("BIOETL_CODEX_ROUTES_FILE", str(tmp_path / "missing.json"))
    with pytest.raises(ValueError, match="absent"):
        apply_local_routes({}, tmp_path)


def test_implicit_host_manifest_does_not_own_other_repositories(
    routes, tmp_path, monkeypatch
):
    _, path, _ = routes
    home = tmp_path / "home"
    target = home / ".config/pc-agent/codex-routes.json"
    target.parent.mkdir(parents=True)
    target.write_bytes(path.read_bytes())
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.delenv("BIOETL_CODEX_ROUTES_FILE", raising=False)
    foreign = tmp_path / "foreign"
    (foreign / ".git").mkdir(parents=True)
    original = {"memory": {"command": "portable"}}
    assert apply_local_routes(original, foreign) == original


def test_toml_publication_refuses_a_concurrent_edit(tmp_path):
    path = tmp_path / "config.toml"
    before = b'model = "before"\n'
    other = b'model = "other-client"\n'
    path.write_bytes(other)
    with pytest.raises(ValueError, match="Concurrent"):
        setup_mcp._write_user_toml(path, 'model = "program"\n', before=before)
    assert path.read_bytes() == other
    assert not list(tmp_path.glob("*.pending"))


def test_toml_publication_has_no_invalid_intermediate_file(tmp_path, monkeypatch):
    path = tmp_path / "config.toml"
    before = b'model = "before"\r\n'
    path.write_bytes(before)
    replace = setup_mcp.os.replace

    def checked_replace(pending, destination):
        import tomllib

        assert destination.read_bytes() == before
        tomllib.loads(destination.read_text(encoding="utf-8"))
        tomllib.loads(pending.read_text(encoding="utf-8"))
        replace(pending, destination)

    monkeypatch.setattr(setup_mcp.os, "replace", checked_replace)
    setup_mcp._write_user_toml(path, 'model = "program"\n', before=before)
    assert path.read_bytes() == b'model = "program"\n'
