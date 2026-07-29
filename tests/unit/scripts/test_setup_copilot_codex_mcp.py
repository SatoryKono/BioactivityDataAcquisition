# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for Codex/Copilot MCP workspace setup."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.ai.codex import setup_mcp


pytestmark = pytest.mark.unit


def _to_bash_path(path: Path) -> str:
    value = path.as_posix()
    if len(value) >= 3 and value[1] == ":" and value[2] == "/":
        return f"/mnt/{value[0].lower()}{value[2:]}"
    return value


def _seed_workspace_mcp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path]:
    """Create a workspace with managed MCP configs under a fake HOME."""
    workspace_root = tmp_path / "workspace"
    fake_home = tmp_path / "runtime-home"
    workspace_root.mkdir()
    fake_home.mkdir()
    monkeypatch.setattr(setup_mcp.Path, "home", lambda: fake_home)
    assert (
        setup_mcp.main(
            [
                "--root",
                str(workspace_root),
                "--workspace-root",
                str(workspace_root),
                "--profile",
                "shared",
                "--transport-mode",
                "shared",
                "--skip-codex-validation",
                "--skip-gemini-settings",
            ]
        )
        == 0
    )
    return workspace_root, fake_home


def test_core_profile_omits_high_privilege_servers_from_local_projections(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--profile core must shrink local IDE projections but keep tracked full inventory."""
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    workspace_root = tmp_path / "workspace-root"
    output_root = tmp_path / "output-root"
    workspace_root.mkdir()
    exit_code = setup_mcp.main(
        [
            "--root",
            str(output_root),
            "--workspace-root",
            str(workspace_root),
            "--skip-codex",
            "--skip-codex-config",
            "--skip-gemini-settings",
            "--profile",
            "core",
        ]
    )
    assert exit_code == 0

    tracked = json.loads((output_root / ".mcp.json").read_text(encoding="utf-8"))
    cursor = json.loads(
        (output_root / ".cursor" / "mcp.json").read_text(encoding="utf-8")
    )
    vscode = json.loads(
        (output_root / ".vscode" / "mcp.json").read_text(encoding="utf-8")
    )
    tracked_names = set(tracked["mcpServers"])
    cursor_names = set(cursor["mcpServers"])
    vscode_names = set(vscode["servers"])

    assert "docker" in tracked_names
    assert "neo4j-memory" in tracked_names
    assert "docker" not in cursor_names
    assert "neo4j-memory" not in cursor_names
    assert "docker" not in vscode_names
    assert "memory" in cursor_names
    assert "github" in cursor_names
    assert not (tracked_names & setup_mcp.REMOVED_MCP_SERVER_NAMES)
    assert not (cursor_names & setup_mcp.REMOVED_MCP_SERVER_NAMES)


def test_shared_transport_mode_rewrites_local_projections_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--transport-mode shared emits localhost HTTP for catalog servers on local IDE only."""
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    workspace_root = tmp_path / "workspace-root"
    output_root = tmp_path / "output-root"
    workspace_root.mkdir()

    exit_code = setup_mcp.main(
        [
            "--root",
            str(output_root),
            "--workspace-root",
            str(workspace_root),
            "--skip-codex",
            "--skip-codex-config",
            "--skip-gemini-settings",
            "--profile",
            "shared",
            "--transport-mode",
            "shared",
        ]
    )
    assert exit_code == 0

    tracked = json.loads((output_root / ".mcp.json").read_text(encoding="utf-8"))
    cursor = json.loads(
        (output_root / ".cursor" / "mcp.json").read_text(encoding="utf-8")
    )
    # Portable SSOT stays stdio wrappers for thrash servers.
    assert "command" in tracked["mcpServers"]["adr-analysis"]
    assert tracked["mcpServers"]["adr-analysis"].get("type") != "http"
    # Local projection uses shared HTTP URL.
    adr = cursor["mcpServers"]["adr-analysis"]
    assert adr["type"] == "http"
    assert adr["url"] == setup_mcp.MCP_SHARED_SERVER_ENDPOINTS["adr-analysis"]
    assert adr["url"].startswith(setup_mcp.APPROVED_LOCAL_MCP_BASE_URL_PREFIXES)
    assert "brave-search" in cursor["mcpServers"]
    assert cursor["mcpServers"]["brave-search"]["type"] == "http"
    # Docker thrash leaders on the shared plane (single container per image).
    for thrash in ("grafana", "prometheus", "brave-search"):
        assert thrash in cursor["mcpServers"]
        assert thrash in setup_mcp.MCP_SHARED_SERVER_ENDPOINTS
        entry = cursor["mcpServers"][thrash]
        assert entry["type"] == "http"
        assert entry["url"] == setup_mcp.MCP_SHARED_SERVER_ENDPOINTS[thrash]
        assert "command" not in entry
    # Stateful servers use the same singleton plane with an explicit state model.
    assert cursor["mcpServers"]["memory"]["type"] == "http"
    assert cursor["mcpServers"]["filesystem"]["type"] == "http"


def test_local_http_server_rejects_non_localhost_url() -> None:
    with pytest.raises(ValueError, match="localhost prefixes"):
        setup_mcp._local_http_server("https://evil.example/mcp")


def test_shared_endpoints_sync_with_catalog() -> None:
    """MCP_SHARED_SERVER_ENDPOINTS must match shared-servers.json ports/paths."""
    catalog_path = (
        Path(__file__).resolve().parents[3]
        / "scripts"
        / "ops"
        / "runtime"
        / "mcp"
        / "shared-servers.json"
    )
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    servers = catalog["servers"]
    assert set(servers) == set(setup_mcp.MCP_SHARED_SERVER_ENDPOINTS)
    canonical = set(setup_mcp._canonical_servers(Path.cwd(), profile="full"))
    assert set(servers) == canonical - {"deepwiki", "ref"}
    for name, entry in servers.items():
        path = entry.get("path") or "/mcp"
        expected = f"http://127.0.0.1:{int(entry['port'])}{path}"
        assert setup_mcp.MCP_SHARED_SERVER_ENDPOINTS[name] == expected


def test_shared_launcher_enforces_singleton_and_loopback() -> None:
    launcher = (
        Path(__file__).resolve().parents[3] / "scripts/ops/runtime/mcp/start-shared.sh"
    ).read_text(encoding="utf-8")
    assert "flock 9" in launcher
    assert '"--host",' in launcher
    assert "bind_host" in launcher
    assert "start_new_session=True" in launcher
    assert '"unmanaged_ready"' in launcher
    assert "readiness_timeout_sec" in launcher


def test_default_local_transport_is_shared_http(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Daily default: stable profile + shared HTTP for catalog servers in profile."""
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    workspace_root = tmp_path / "workspace-root"
    output_root = tmp_path / "output-root"
    workspace_root.mkdir()

    assert setup_mcp.DEFAULT_LOCAL_TRANSPORT_MODE == "shared"
    assert setup_mcp.DEFAULT_LOCAL_PROFILE == "stable"

    exit_code = setup_mcp.main(
        [
            "--root",
            str(output_root),
            "--workspace-root",
            str(workspace_root),
            "--skip-codex",
            "--skip-codex-config",
            "--skip-gemini-settings",
            # omit --profile / --transport-mode → daily least-privilege defaults
        ]
    )
    assert exit_code == 0
    cursor = json.loads(
        (output_root / ".cursor" / "mcp.json").read_text(encoding="utf-8")
    )
    adr = cursor["mcpServers"]["adr-analysis"]
    assert adr["type"] == "http"
    assert adr["url"] == setup_mcp.MCP_SHARED_SERVER_ENDPOINTS["adr-analysis"]
    # Explicit stdio still available for single-client fallback.
    exit_code = setup_mcp.main(
        [
            "--root",
            str(output_root),
            "--workspace-root",
            str(workspace_root),
            "--skip-codex",
            "--skip-codex-config",
            "--skip-gemini-settings",
            "--profile",
            "shared",
            "--transport-mode",
            "stdio",
        ]
    )
    assert exit_code == 0
    cursor = json.loads(
        (output_root / ".cursor" / "mcp.json").read_text(encoding="utf-8")
    )
    adr = cursor["mcpServers"]["adr-analysis"]
    assert "command" in adr
    assert adr.get("type") != "http"


def test_codex_http_servers_have_no_env_tables(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Codex rejects env on streamable_http — never emit [mcp_servers.X.env] for HTTP."""
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(setup_mcp.Path, "home", lambda: fake_home)
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    exit_code = setup_mcp.main(
        [
            "--root",
            str(workspace_root),
            "--workspace-root",
            str(workspace_root),
            "--profile",
            "shared",
            "--transport-mode",
            "shared",
            "--skip-codex-validation",
            "--skip-gemini-settings",
        ]
    )
    assert exit_code == 0
    toml = (fake_home / ".codex" / "config.toml").read_text(encoding="utf-8")
    for name in setup_mcp.MCP_SHARED_SERVER_ENDPOINTS:
        if f"[mcp_servers.{name}]" not in toml:
            continue
        assert f"[mcp_servers.{name}.env]" not in toml, name
        assert f'url = "{setup_mcp.MCP_SHARED_SERVER_ENDPOINTS[name]}"' in toml


def test_hybrid_transport_mode_rewrites_catalog_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    workspace_root = tmp_path / "workspace-root"
    output_root = tmp_path / "output-root"
    workspace_root.mkdir()

    exit_code = setup_mcp.main(
        [
            "--root",
            str(output_root),
            "--workspace-root",
            str(workspace_root),
            "--skip-codex",
            "--skip-codex-config",
            "--skip-gemini-settings",
            "--profile",
            "shared",
            "--transport-mode",
            "hybrid",
        ]
    )
    assert exit_code == 0
    cursor = json.loads(
        (output_root / ".cursor" / "mcp.json").read_text(encoding="utf-8")
    )
    assert cursor["mcpServers"]["adr-analysis"]["type"] == "http"
    assert cursor["mcpServers"]["memory"]["type"] == "http"


def test_main_uses_workspace_root_for_generated_server_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Generated server paths should follow the requested workspace root."""
    # Isolate host XDG cache so the fallback scenario stays deterministic (#6417).
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    workspace_root = tmp_path / "workspace-root"
    output_root = tmp_path / "output-root"
    workspace_root.mkdir()

    exit_code = setup_mcp.main(
        [
            "--root",
            str(output_root),
            "--workspace-root",
            str(workspace_root),
            "--skip-codex",
            "--skip-codex-config",
            "--profile",
            "full",
            # Path assertions compare portable stdio inventory across projections.
            "--transport-mode",
            "stdio",
        ]
    )
    assert exit_code == 0

    payload = json.loads((output_root / ".mcp.json").read_text(encoding="utf-8"))
    qodo_payload = json.loads(
        (output_root / ".qodo" / "mcp.json").read_text(encoding="utf-8")
    )
    codex_settings = json.loads(
        (output_root / ".codex" / "settings.json").read_text(encoding="utf-8")
    )
    devin_config = json.loads(
        (output_root / ".devin" / "config.json").read_text(encoding="utf-8")
    )
    gemini_settings = json.loads(
        (output_root / ".gemini" / "settings.json").read_text(encoding="utf-8")
    )
    zed_payload = json.loads(
        (output_root / ".zed" / "mcp.json").read_text(encoding="utf-8")
    )
    servers = payload["mcpServers"]
    wrapper_suffix = ".ps1" if os.name == "nt" else ".sh"
    expected_servers = {
        "memory",
        "filesystem",
        "fetch",
        "github",
        "docker",
        "context7",
        "ast-grep",
        "mcp-code-interpreter",
        "prometheus",
        "grafana",
        "brave-search",
        "neo4j-cypher",
        "neo4j-memory",
        "mermaid",
        "deja",
        "adr-analysis",
        "mutmut",
        "code-analyzer",
        "github-actions",
        "deepwiki",
        "ref",
    }
    removed_servers = {
        "sequential-thinking",
        "pdf",
        "needle",
        "docker-docs",
        "dockerhub",
        "paper-search",
        "openaiDeveloperDocs",
        "sonarqube",
        "chembl",
        "pubchem",
        "pubmed",
        "biomoltechDocs",
        "mintlify",
    }

    runtime_servers = codex_settings["mcpServers"]
    devin_servers = devin_config["mcpServers"]
    assert set(servers) == expected_servers
    assert set(devin_servers) == set(servers)
    for server_name, server_config in servers.items():
        if server_name != "ref":
            assert devin_servers[server_name] == server_config
    expected_devin_ref = dict(servers["ref"])
    expected_devin_ref.pop("env_http_headers")
    expected_devin_ref["headers"] = {
        "x-ref-api-key": "$REF_TOOL_API_KEY",
    }
    assert devin_servers["ref"] == expected_devin_ref
    assert qodo_payload["mcpServers"] == servers
    assert zed_payload["mcpServers"] == servers
    assert not removed_servers.intersection(servers)
    assert not removed_servers.intersection(gemini_settings["mcpServers"])
    assert servers["filesystem"]["args"][0] == (
        f"scripts/ai/mcp/mcp_filesystem_wrapper{wrapper_suffix}"
    )
    assert devin_servers["filesystem"]["args"][0] == (
        f"scripts/ai/mcp/mcp_filesystem_wrapper{wrapper_suffix}"
    )
    assert runtime_servers["filesystem"]["args"][0] == str(
        (
            workspace_root / f"scripts/ai/mcp/mcp_filesystem_wrapper{wrapper_suffix}"
        ).resolve()
    )
    assert servers["memory"]["args"][0].endswith(
        ("mcp_memory_wrapper.sh", "mcp_memory_wrapper.ps1")
    )
    assert (
        servers["memory"]["env"]["MEMORY_FILE_PATH"]
        == "docs/00-project/ai/memory/mcp-memory.json"
    )
    assert runtime_servers["memory"]["env"]["MEMORY_FILE_PATH"] == str(
        (workspace_root / "docs/00-project/ai/memory/mcp-memory.json").resolve()
    )
    assert servers["fetch"]["args"][0] == (
        f"scripts/ai/mcp/mcp_fetch_wrapper{wrapper_suffix}"
    )
    assert runtime_servers["fetch"]["args"][0] == str(
        (workspace_root / f"scripts/ai/mcp/mcp_fetch_wrapper{wrapper_suffix}").resolve()
    )
    assert servers["fetch"]["env"] == {
        "UV_CACHE_DIR": ".cache/uv-cache",
        "UV_TOOL_DIR": ".cache/uv-tools",
        "NPM_CONFIG_CACHE": ".cache/npm-cache",
    }
    runtime_cache_root = Path.home() / ".cache/bioetl-mcp"
    assert runtime_servers["fetch"]["env"] == {
        "UV_CACHE_DIR": str(runtime_cache_root / "uv-cache"),
        "UV_TOOL_DIR": str(runtime_cache_root / "uv-tools"),
        "NPM_CONFIG_CACHE": str(runtime_cache_root / "npm-cache"),
    }
    assert runtime_servers["context7"]["env"]["NPM_CONFIG_CACHE"] == str(
        runtime_cache_root / "npm-cache"
    )
    assert servers["github"]["args"][0] == (
        f"scripts/ai/mcp/github-mcp-wrapper{wrapper_suffix}"
    )
    assert runtime_servers["github"]["args"][0] == str(
        (
            workspace_root / f"scripts/ai/mcp/github-mcp-wrapper{wrapper_suffix}"
        ).resolve()
    )
    assert servers["docker"]["args"][0] == (
        f"scripts/ai/mcp/mcp_docker_wrapper{wrapper_suffix}"
    )
    assert servers["context7"]["args"][0] == (
        f"scripts/ai/mcp/mcp_context7_wrapper{wrapper_suffix}"
    )
    assert servers["grafana"]["args"][0] == (
        f"scripts/ai/mcp/mcp_grafana_wrapper{wrapper_suffix}"
    )
    assert servers["mermaid"]["args"][0] == (
        f"scripts/ai/mcp/mcp_mermaid_wrapper{wrapper_suffix}"
    )
    assert runtime_servers["mermaid"]["args"][0] == str(
        (
            workspace_root / f"scripts/ai/mcp/mcp_mermaid_wrapper{wrapper_suffix}"
        ).resolve()
    )
    for server_name, wrapper_stem in {
        "deja": "mcp_deja_wrapper",
        "adr-analysis": "mcp_adr_analysis_wrapper",
        "mutmut": "mcp_mutmut_wrapper",
        "code-analyzer": "mcp_code_analyzer_wrapper",
        "github-actions": "mcp_github_actions_wrapper",
    }.items():
        assert servers[server_name]["args"][0] == (
            f"scripts/ai/mcp/{wrapper_stem}{wrapper_suffix}"
        )
        assert runtime_servers[server_name]["args"][0] == str(
            (
                workspace_root / f"scripts/ai/mcp/{wrapper_stem}{wrapper_suffix}"
            ).resolve()
        )
    assert servers["deja"]["env"]["NPM_CONFIG_CACHE"] == ".cache/npm-cache"
    assert servers["adr-analysis"]["env"] == {
        "PROJECT_PATH": ".",
        "ADR_PATH": "docs/02-architecture/decisions",
    }
    assert runtime_servers["adr-analysis"]["env"] == {
        "PROJECT_PATH": str(workspace_root.resolve()),
        "ADR_PATH": str((workspace_root / "docs/02-architecture/decisions").resolve()),
        "NPM_CONFIG_CACHE": str(runtime_cache_root / "npm-cache"),
    }
    assert servers["mutmut"]["env"]["MUTMUT_PROJECT_PATH"] == "."
    assert servers["code-analyzer"]["env"]["PROJECT_PATH"] == "."
    assert servers["deepwiki"]["url"] == "https://mcp.deepwiki.com/mcp"
    assert servers["ref"]["type"] == "http"
    assert servers["ref"]["url"] == "https://api.ref.tools/mcp"
    assert (
        gemini_settings["mcpServers"]["ref"]["httpUrl"] == "https://api.ref.tools/mcp"
    )


def test_main_recreates_empty_workspace_json_configs(tmp_path: Path) -> None:
    """Empty local runtime config files should be treated as missing and rewritten."""
    workspace_root = tmp_path / "workspace-root"
    output_root = tmp_path / "output-root"
    workspace_root.mkdir()
    (output_root / ".codex").mkdir(parents=True)
    (output_root / ".devin").mkdir(parents=True)
    (output_root / ".gemini").mkdir(parents=True)
    (output_root / ".codex" / "settings.json").write_text("", encoding="utf-8")
    (output_root / ".devin" / "config.json").write_text("", encoding="utf-8")
    (output_root / ".gemini" / "settings.json").write_text("", encoding="utf-8")

    exit_code = setup_mcp.main(
        [
            "--root",
            str(output_root),
            "--workspace-root",
            str(workspace_root),
            "--skip-codex",
            "--skip-codex-config",
        ]
    )

    assert exit_code == 0
    shared_fs_url = setup_mcp.MCP_SHARED_SERVER_ENDPOINTS["filesystem"]
    assert (
        json.loads(
            (output_root / ".codex" / "settings.json").read_text(encoding="utf-8")
        )["mcpServers"]["filesystem"]["url"]
        == shared_fs_url
    )
    assert (
        json.loads(
            (output_root / ".devin" / "config.json").read_text(encoding="utf-8")
        )["mcpServers"]["filesystem"]["url"]
        == shared_fs_url
    )
    assert (
        json.loads(
            (output_root / ".gemini" / "settings.json").read_text(encoding="utf-8")
        )["mcpServers"]["filesystem"]["httpUrl"]
        == shared_fs_url
    )


def test_devin_projection_is_portable_across_workspace_roots(
    tmp_path: Path,
) -> None:
    """Tracked Devin MCP data should be stable and preserve Devin-owned settings."""
    generated: list[dict[str, object]] = []
    for name in ("first-clone", "second-clone"):
        workspace_root = tmp_path / name / "workspace"
        output_root = tmp_path / name / "output"
        workspace_root.mkdir(parents=True)
        devin_path = output_root / ".devin" / "config.json"
        devin_path.parent.mkdir(parents=True)
        devin_path.write_text(
            json.dumps(
                {
                    "version": 2,
                    "devin": {"org_id": "org-test"},
                    "shell": {"setup_complete": True},
                    "theme_mode": "light",
                    "mcpServers": {"stale": {"command": "old"}},
                }
            ),
            encoding="utf-8",
        )

        assert (
            setup_mcp.main(
                [
                    "--root",
                    str(output_root),
                    "--workspace-root",
                    str(workspace_root),
                    "--skip-codex",
                    "--skip-codex-config",
                    "--skip-gemini-settings",
                ]
            )
            == 0
        )
        generated.append(json.loads(devin_path.read_text(encoding="utf-8")))

    assert generated[0] == generated[1]
    assert generated[0]["devin"] == {"org_id": "org-test"}
    assert generated[0]["shell"] == {"setup_complete": True}
    assert generated[0]["theme_mode"] == "light"
    assert (
        generated[0]["mcpServers"]["filesystem"]["url"]
        == (setup_mcp.MCP_SHARED_SERVER_ENDPOINTS["filesystem"])
    )


def test_skip_codex_validation_still_updates_codex_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Launcher setup should update Codex config without running slow CLI validation."""
    workspace_root = tmp_path / "workspace-root"
    output_root = tmp_path / "output-root"
    fake_home = tmp_path / "home"
    workspace_root.mkdir()
    fake_home.mkdir()
    codex_dir = fake_home / ".codex"
    codex_dir.mkdir()
    codex_config = codex_dir / "config.toml"
    codex_config.write_text(
        """
[mcp_servers.pycharm]
url = "http://127.0.0.1:64342/sse"

[mcp_servers.biomoltechDocs]
url = "https://retired.invalid/mcp"

[mcp_servers.mintlify]
url = "https://retired.invalid/mcp"
""".lstrip(),
        encoding="utf-8",
    )

    def fail_validation(_workspace_root: Path) -> None:
        raise AssertionError("Codex CLI validation should have been skipped")

    monkeypatch.setattr(setup_mcp.Path, "home", lambda: fake_home)
    monkeypatch.setattr(setup_mcp, "_run_codex_validation", fail_validation)

    exit_code = setup_mcp.main(
        [
            "--root",
            str(output_root),
            "--workspace-root",
            str(workspace_root),
            "--skip-codex-validation",
            "--skip-gemini-settings",
        ]
    )

    assert exit_code == 0
    rendered = codex_config.read_text(encoding="utf-8")
    assert "[mcp_servers.pycharm]" in rendered
    assert "[mcp_servers.biomoltechDocs]" not in rendered
    assert "[mcp_servers.mintlify]" not in rendered
    assert "[mcp_servers.filesystem]" in rendered
    assert "[mcp_servers.memory]" in rendered
    assert "[mcp_servers.ref]" in rendered
    assert 'url = "https://api.ref.tools/mcp"' in rendered
    assert 'env_http_headers = { x-ref-api-key = "REF_TOOL_API_KEY" }' in rendered
    assert "?apiKey=" not in rendered
    # Filesystem is routed through a host wrapper that resolves REPO_ROOT at runtime.
    assert "filesystem" in rendered


def test_setup_mcp_reuses_current_config_and_repairs_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pure-Python path: re-running setup is idempotent and repairs drift."""
    workspace_root, fake_home = _seed_workspace_mcp(tmp_path, monkeypatch)
    codex_config = fake_home / ".codex/config.toml"
    workspace_config = workspace_root / ".mcp.json"
    initial_codex_config = codex_config.read_text(encoding="utf-8")
    initial_workspace_config = workspace_config.read_text(encoding="utf-8")

    shared_args = [
        "--root",
        str(workspace_root),
        "--workspace-root",
        str(workspace_root),
        "--profile",
        "shared",
        "--transport-mode",
        "shared",
        "--skip-codex-validation",
        "--skip-gemini-settings",
    ]
    assert setup_mcp.main(shared_args) == 0
    assert codex_config.read_text(encoding="utf-8") == initial_codex_config
    assert workspace_config.read_text(encoding="utf-8") == initial_workspace_config

    drifted = json.loads(workspace_config.read_text(encoding="utf-8"))
    drifted["mcpServers"]["filesystem"]["args"][0] = "unexpected-wrapper"
    workspace_config.write_text(json.dumps(drifted), encoding="utf-8")

    assert setup_mcp.main(shared_args) == 0
    repaired_payload = json.loads(workspace_config.read_text(encoding="utf-8"))
    wrapper_suffix = ".ps1" if os.name == "nt" else ".sh"
    assert repaired_payload["mcpServers"]["filesystem"]["args"][0] == (
        f"scripts/ai/mcp/mcp_filesystem_wrapper{wrapper_suffix}"
    )


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="bash ensure-mcp helper is exercised under WSL/Linux CI (bash hangs on this host)",
)
def test_ensure_mcp_shell_reuses_current_config_and_repairs_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Shell helper should report unchanged config and repair actual drift."""
    root = Path(__file__).resolve().parents[3]
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    workspace_root, fake_home = _seed_workspace_mcp(tmp_path, monkeypatch)

    runtime_env = os.environ.copy()
    runtime_env.update(
        {
            "HOME": _to_bash_path(fake_home),
            "REPO_ROOT": _to_bash_path(workspace_root),
            "CODEX_VALIDATE_MCP_LIST": "0",
            # Bound but generous: WSL cold-start + shared-plane materialize.
            "CODEX_MCP_SETUP_TIMEOUT": "90",
            "CODEX_MCP_PROFILE": "shared",
            "CODEX_MCP_TRANSPORT_MODE": "shared",
        }
    )
    runtime_env.pop("XDG_CACHE_HOME", None)
    ensure_script = _to_bash_path(root / "scripts/ai/codex/helper/ensure-mcp.sh")
    codex_config = fake_home / ".codex/config.toml"
    initial_codex_config = codex_config.read_text(encoding="utf-8")
    bash_root = _to_bash_path(root)
    ensure_timeout_seconds = 120

    unchanged = subprocess.run(
        ["bash", ensure_script, "--ensure"],
        cwd=bash_root,
        env=runtime_env,
        capture_output=True,
        text=True,
        check=False,
        timeout=ensure_timeout_seconds,
    )

    assert unchanged.returncode == 0, unchanged.stderr
    assert "[mcp] MCP config is ready" in unchanged.stdout
    if "(unchanged)" in unchanged.stdout:
        assert codex_config.read_text(encoding="utf-8") == initial_codex_config

    workspace_config = workspace_root / ".mcp.json"
    drifted = json.loads(workspace_config.read_text(encoding="utf-8"))
    drifted["mcpServers"]["filesystem"]["args"][0] = "unexpected-wrapper"
    workspace_config.write_text(json.dumps(drifted), encoding="utf-8")

    repaired = subprocess.run(
        ["bash", ensure_script, "--ensure"],
        cwd=bash_root,
        env=runtime_env,
        capture_output=True,
        text=True,
        check=False,
        timeout=ensure_timeout_seconds,
    )

    assert repaired.returncode == 0, repaired.stderr
    assert "[mcp] MCP config is ready (refreshed)" in repaired.stdout
    repaired_payload = json.loads(workspace_config.read_text(encoding="utf-8"))
    wrapper_suffix = ".ps1" if os.name == "nt" else ".sh"
    assert repaired_payload["mcpServers"]["filesystem"]["args"][0] == (
        f"scripts/ai/mcp/mcp_filesystem_wrapper{wrapper_suffix}"
    )
