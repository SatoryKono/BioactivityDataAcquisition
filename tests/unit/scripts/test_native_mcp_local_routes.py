"""Native route synchronization must preserve isolation and user-owned settings."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.ai.codex import setup_mcp
from scripts.ai.codex.local_mcp_routes import apply_local_routes
from scripts.ai.mcp import session_client
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


def test_relative_worktree_links_use_the_registered_common_directory(routes, tmp_path):
    root, path, data = routes
    checkout = tmp_path / "worktree"
    checkout.mkdir()
    gitdir = root / ".git/worktrees/worktree"
    gitdir.mkdir(parents=True)
    (checkout / ".git").write_text(
        "gitdir: ../repo/.git/worktrees/worktree\n", encoding="utf-8"
    )
    (gitdir / "gitdir").write_text("../../../../worktree/.git\n", encoding="utf-8")
    (gitdir / "commondir").write_text("../..\n", encoding="utf-8")

    actual = apply_local_routes({"memory": {}}, checkout, manifest=path)

    assert actual == data["entries"]


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


def test_broken_nested_git_link_does_not_fall_through_to_parent(routes):
    root, _, _ = routes
    nested = root / "nested"
    nested.mkdir()
    try:
        (nested / ".git").symlink_to(nested / "missing")
    except OSError:
        pytest.skip("Symbolic links are unavailable in this environment")
    with pytest.raises(PermissionError, match="reparse point"):
        session_root(nested, lambda candidate: candidate)


def test_implicit_dispatcher_manifest_is_required(tmp_path, monkeypatch):
    monkeypatch.setattr(session_client, "__file__", str(tmp_path / "session_client.py"))
    with pytest.raises(PermissionError, match="manifest is absent"):
        session_client._verify_dispatcher()


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


def test_codex_config_lock_covers_read_and_publication(routes, monkeypatch, tmp_path):
    root, manifest, _ = routes
    home = tmp_path / "home"
    default_config = home / ".codex/config.toml"
    default_config.parent.mkdir(parents=True)
    default_config.write_text('model = "user-model"\n', encoding="utf-8")
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.setenv("BIOETL_CODEX_ROUTES_FILE", str(manifest))
    lock = default_config.with_name(default_config.name + ".bioetl.lock")
    probe = """
import sys
from pathlib import Path

with Path(sys.argv[1]).open("a+b") as handle:
    try:
        if sys.platform == "win32":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        sys.exit(71)
"""

    def try_lock():
        return subprocess.run(
            [sys.executable, "-I", "-c", probe, str(lock)],
            timeout=30,
            check=False,
        ).returncode

    read = Path.read_bytes
    publish = setup_mcp._write_user_toml
    locked_reads = []

    def checked_read(path):
        if path == default_config:
            locked_reads.append(try_lock())
        return read(path)

    def checked_publish(path, rendered, *, before):
        assert try_lock() == 71
        publish(path, rendered, before=before)

    monkeypatch.setattr(Path, "read_bytes", checked_read)
    monkeypatch.setattr(setup_mcp, "_write_user_toml", checked_publish)
    setup_mcp._write_codex_config(root, profile="stable", transport_mode="shared")
    assert locked_reads == [71, 71]
    assert try_lock() == 0
    assert 'model = "user-model"' in default_config.read_text(encoding="utf-8")


def test_removed_default_checkout_does_not_block_unrelated_generation(
    routes, tmp_path, monkeypatch
):
    root, path, data = routes
    (root / ".git").rmdir()
    home = tmp_path / "home"
    default = home / ".config/pc-agent/codex-routes.json"
    default.parent.mkdir(parents=True)
    default.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.delenv("BIOETL_CODEX_ROUTES_FILE", raising=False)
    baseline = {"memory": {"command": "baseline"}}
    assert apply_local_routes(baseline, tmp_path) is baseline
    with pytest.raises(FileNotFoundError):
        apply_local_routes(baseline, tmp_path, manifest=path)
    monkeypatch.setenv("BIOETL_CODEX_ROUTES_FILE", str(default))
    with pytest.raises(FileNotFoundError):
        apply_local_routes(baseline, tmp_path)


def test_managed_toml_headers_are_parsed_with_comments_quotes_and_multiline_values():
    import tomllib

    original = (
        'model = "user-model"\n'
        'notes = """unchanged\n[mcp_servers.memory.tools.fake] # not a header\n"""\n'
        '[mcp_servers.memory] # transport\ncommand = "old"\n'
        '[mcp_servers."memory".tools."read_graph"] # policy\napproval_mode = "approve"\n'
        '[mcp_servers."custom.name"] # unmanaged\ncommand = "custom"\n'
        "notes = '''unchanged\n[mcp_servers.memory] # also a value\n'''\n"
    )
    expected = tomllib.loads(original)
    stripped = setup_mcp._strip_managed_mcp_blocks(original, {"memory"})
    result = tomllib.loads(stripped + '\n[mcp_servers.memory]\ncommand = "new"\n')
    assert result["model"] == expected["model"]
    assert result["notes"] == expected["notes"]
    assert (
        result["mcp_servers"]["custom.name"] == expected["mcp_servers"]["custom.name"]
    )
    assert result["mcp_servers"]["memory"] == {"command": "new"}


def test_sync_preserves_fractional_timeouts(routes, monkeypatch, tmp_path):
    import tomllib

    root, manifest, _ = routes
    monkeypatch.setenv("BIOETL_CODEX_ROUTES_FILE", str(manifest))
    home = tmp_path / "home"
    config = home / ".codex/config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(
        '[mcp_servers.memory]\ncommand="old"\nstartup_timeout_sec=0.25\ntool_timeout_sec=0.5\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(Path, "home", lambda: home)
    setup_mcp._write_codex_config(root, profile="stable", transport_mode="shared")
    values = tomllib.loads(config.read_text(encoding="utf-8"))["mcp_servers"]["memory"]
    assert values["startup_timeout_sec"] == 0.25 and values["tool_timeout_sec"] == 0.5


def test_policy_survives_when_its_server_is_inactive(routes, monkeypatch, tmp_path):
    import tomllib

    root, manifest, _ = routes
    monkeypatch.setenv("BIOETL_CODEX_ROUTES_FILE", str(manifest))
    home = tmp_path / "home"
    config = home / ".codex/config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(
        "[mcp_servers.prometheus]\n"
        'url = "http://localhost/fixture"\n'
        'disabled_tools = ["dangerous_operation"]\n'
        "tool_timeout_sec = 0.5\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(Path, "home", lambda: home)
    setup_mcp._write_codex_config(root, profile="stable", transport_mode="shared")
    stable = config.read_text(encoding="utf-8")
    assert "prometheus" not in tomllib.loads(stable)["mcp_servers"]
    assert "http://localhost/fixture" not in stable
    setup_mcp._write_codex_config(root, profile="full", transport_mode="shared")
    restored = tomllib.loads(config.read_text(encoding="utf-8"))["mcp_servers"]
    assert restored["prometheus"]["disabled_tools"] == ["dangerous_operation"]
    assert restored["prometheus"]["tool_timeout_sec"] == 0.5


def test_strip_managed_inline_server_keeps_other_entries():
    import tomllib

    source = (
        "[mcp_servers]\n"
        'memory = { command = "old" }\n'
        '"custom.name" = { command = "custom" } # keep this comment\n'
    )
    filtered = setup_mcp._strip_managed_mcp_blocks(source, {"memory"})
    assert "# keep this comment" in filtered
    actual = tomllib.loads(filtered + '\n[mcp_servers.memory]\ncommand = "new"\n')
    assert actual["mcp_servers"] == {
        "memory": {"command": "new"},
        "custom.name": {"command": "custom"},
    }


@pytest.mark.parametrize("flag", ["--skip-codex-config", "--skip-codex", "--check"])
def test_stage_rejects_options_that_prevent_writing_a_candidate(flag):
    with pytest.raises(SystemExit) as error:
        setup_mcp.main(["--stage-codex-config", flag])
    assert error.value.code == 2


def test_staged_codex_candidate_never_replaces_an_external_edit(
    routes, monkeypatch, tmp_path
):
    import tomllib

    root, manifest, _ = routes
    monkeypatch.setenv("BIOETL_CODEX_ROUTES_FILE", str(manifest))
    home = tmp_path / "home"
    config = home / ".codex/config.toml"
    config.parent.mkdir(parents=True)
    config.write_text('model="before"\n', encoding="utf-8")
    monkeypatch.setattr(Path, "home", lambda: home)
    publish = setup_mcp._write_user_toml

    def editor_save(path, rendered, *, before):
        config.write_text('model="saved-by-editor"\n', encoding="utf-8")
        assert path != config and before is None
        publish(path, rendered, before=before)

    monkeypatch.setattr(setup_mcp, "_write_user_toml", editor_save)
    candidate = setup_mcp._write_codex_config(
        root, profile="stable", transport_mode="shared", stage=True
    )
    assert (
        tomllib.loads(config.read_text(encoding="utf-8"))["model"] == "saved-by-editor"
    )
    assert tomllib.loads(candidate.read_text(encoding="utf-8"))["model"] == "before"
    assert candidate.name.endswith(".candidate")


def test_foreign_git_binding_is_not_probed_before_repository_comparison(
    routes, tmp_path, monkeypatch
):
    from scripts.ai.codex import local_mcp_routes

    root, path, data = routes
    foreign = tmp_path / "foreign-private/.git"
    data["git_common"] = str(foreign)
    path.write_text(json.dumps(data), encoding="utf-8")
    physical = local_mcp_routes._physical

    def observed(value):
        assert value != foreign, "foreign binding was probed before comparison"
        return physical(value)

    monkeypatch.setattr(local_mcp_routes, "_physical", observed)
    with pytest.raises(ValueError, match="another repository"):
        apply_local_routes({"memory": {}}, root, manifest=path)


def test_session_selector_respects_a_dangling_nearest_git_marker(tmp_path, monkeypatch):
    from scripts.ai.mcp import session_client

    outer, inner = tmp_path / "outer", tmp_path / "outer/nested"
    inner.mkdir(parents=True)
    (outer / ".git").mkdir()
    original = session_client.os.path.lexists
    monkeypatch.setattr(
        session_client.os.path,
        "lexists",
        lambda path: True if Path(path) == inner / ".git" else original(path),
    )

    def validate(path):
        assert path == inner
        raise PermissionError("Broken nearest marker")

    with pytest.raises(PermissionError, match="nearest marker"):
        session_root(inner, validate)


def test_selector_main_refuses_missing_dispatcher_before_loading_host(
    tmp_path, monkeypatch
):
    from types import SimpleNamespace
    from unittest.mock import Mock
    from scripts.ai.mcp import session_client

    monkeypatch.setattr(session_client, "__file__", str(tmp_path / "session_client.py"))
    monkeypatch.setattr(
        session_client,
        "sys",
        SimpleNamespace(
            executable=str(session_client.PYTHON),
            flags=SimpleNamespace(isolated=True, no_site=True),
            dont_write_bytecode=True,
        ),
    )
    load = Mock(side_effect=AssertionError("Unqualified host loaded"))
    monkeypatch.setattr(session_client.importlib.util, "spec_from_file_location", load)
    with pytest.raises(PermissionError, match="dispatcher manifest"):
        session_client.main()
    load.assert_not_called()


def test_dangling_default_manifest_is_rejected_instead_of_portable_fallback(
    tmp_path, monkeypatch
):
    from scripts.ai.codex import local_mcp_routes as routes

    home = tmp_path / "home"
    marker = home / ".config/pc-agent/codex-routes.json"
    marker.parent.mkdir(parents=True)
    try:
        marker.symlink_to(marker.with_name("missing.json"))
    except OSError:
        pytest.skip("Symbolic links are unavailable")
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.delenv("BIOETL_CODEX_ROUTES_FILE", raising=False)
    with pytest.raises(ValueError, match="reparse point"):
        routes.apply_local_routes({"memory": {"command": "portable"}}, tmp_path)
