"""Generate Windows-native Grok MCP config for this BioETL checkout.

Writes:
  - ~/.grok/config.toml  (merges MCP into existing user UI settings)
  - <repo>/.grok/config.toml  (project override; gitignored)

Uses absolute paths and pwsh + .ps1 wrappers so Grok does not spawn WSL bash
from the portable tracked .mcp.json.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from scripts.ai.codex.setup_mcp import (
    _add_startup_timeouts,
    _canonical_servers,
    _toml_array,
    _toml_key,
    _toml_string,
)

CORE_ENABLED = frozenset(
    {
        "memory",
        "filesystem",
        "fetch",
        "github",
        "github-actions",
        "brave-search",
        "adr-analysis",
        "code-analyzer",
        "ast-grep",
        "mermaid",
        "deepwiki",
        "ref",
        "dockerhub",
    }
)


def _render_mcp_block(
    servers: dict[str, dict[str, Any]],
    *,
    repo_root: Path,
) -> str:
    lines: list[str] = [
        "[mcp]",
        "max_output_bytes = 40000",
        "",
    ]
    if "dockerhub" not in servers:
        servers = dict(servers)
        servers["dockerhub"] = {
            "command": "pwsh",
            "args": [
                "-NoProfile",
                "-File",
                str((repo_root / "scripts/ai/mcp/mcp_dockerhub_wrapper.ps1").resolve()),
            ],
            "startup_timeout_sec": 180,
        }

    for name, server in servers.items():
        enabled = name in CORE_ENABLED
        lines.append(f"[mcp_servers.{name}]")
        lines.append(f"enabled = {str(enabled).lower()}")
        if "url" in server and "command" not in server:
            lines.append(f"url = {_toml_string(str(server['url']))}")
        else:
            command = str(server.get("command", "pwsh"))
            args = [str(item) for item in server.get("args", [])]
            if command in {"powershell", "pwsh"} or (
                args and args[0].endswith(".ps1")
            ):
                command = "pwsh"
                if args and not args[0].startswith("-"):
                    args = ["-NoProfile", "-File", *args]
            lines.append(f"command = {_toml_string(command)}")
            lines.append(f"args = {_toml_array(args)}")
        timeout = max(int(server.get("startup_timeout_sec") or 120), 120)
        lines.append(f"startup_timeout_sec = {timeout}")
        env = server.get("env") or {}
        if env:
            lines.append(f"[mcp_servers.{name}.env]")
            for env_key in sorted(env):
                lines.append(
                    f"{_toml_key(env_key)} = {_toml_string(str(env[env_key]))}"
                )
        lines.append("")
    return "\n".join(lines)


def _preserve_user_preamble(existing: str) -> str:
    """Keep non-MCP sections from an existing user config.toml."""
    if not existing.strip():
        return (
            "[cli]\n"
            'installer = "npm"\n'
            "auto_update = true\n\n"
            "[ui]\n"
            "max_thoughts_width = 120\n"
            'fork_secondary_model = "grok-build"\n'
            "yolo = false\n"
            "compact_mode = false\n"
            'permission_mode = "always-approve"\n\n'
            "[marketplace]\n"
            "default_skills_installs_purged = true\n"
            "official_marketplace_auto_installed = true\n\n"
            "[[marketplace.sources]]\n"
            'name = "xAI Official"\n'
            'git = "https://github.com/xai-org/plugin-marketplace.git"\n\n'
        )
    lines = existing.splitlines()
    kept: list[str] = []
    skip = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[mcp]") or stripped.startswith("[mcp_servers."):
            skip = True
            continue
        if skip:
            if stripped.startswith("[") and not stripped.startswith("[mcp"):
                skip = False
            else:
                continue
        if stripped.startswith("# BioETL Windows-native MCP"):
            continue
        if stripped.startswith("# Generated for Grok on Windows"):
            continue
        if stripped.startswith("# Core servers enabled"):
            continue
        if stripped.startswith("# Re-run"):
            continue
        if stripped.startswith("# Toggle:"):
            continue
        if stripped.startswith(
            "# ---------------------------------------------------------------------------"
        ):
            continue
        if stripped.startswith("# Machine-local Grok MCP"):
            continue
        if stripped.startswith("# DO NOT COMMIT absolute paths"):
            continue
        kept.append(line)
    return "\n".join(kept).rstrip() + "\n\n"


def generate(
    *,
    repo_root: Path,
    user_config: Path,
    project_config: Path,
) -> tuple[Path, Path]:
    servers = _canonical_servers(repo_root, portable_workspace_paths=False)
    _add_startup_timeouts(servers)
    servers["dockerhub"] = {
        "command": "pwsh",
        "args": [
            "-NoProfile",
            "-File",
            str((repo_root / "scripts/ai/mcp/mcp_dockerhub_wrapper.ps1").resolve()),
        ],
        "startup_timeout_sec": 180,
    }
    mcp_block = _render_mcp_block(servers, repo_root=repo_root)

    banner = (
        "# ---------------------------------------------------------------------------\n"
        "# BioETL Windows-native MCP (machine-local)\n"
        "# Generated for Grok on Windows — uses pwsh + .ps1 wrappers, absolute caches.\n"
        "# Core servers enabled; service-backed optional servers disabled by default.\n"
        "# Re-run: python -m scripts.ai.mcp.generate_grok_windows_mcp\n"
        "# Toggle: /mcps  or  set enabled=true below when tokens/services are ready.\n"
        "# ---------------------------------------------------------------------------\n"
    )

    existing_user = (
        user_config.read_text(encoding="utf-8") if user_config.exists() else ""
    )
    user_config.parent.mkdir(parents=True, exist_ok=True)
    user_config.write_text(
        _preserve_user_preamble(existing_user) + banner + mcp_block,
        encoding="utf-8",
    )

    project_config.parent.mkdir(parents=True, exist_ok=True)
    project_config.write_text(
        "# Machine-local Grok MCP for BioETL (Windows-native).\n"
        "# DO NOT COMMIT absolute paths — keep this file local/gitignored.\n\n"
        + mcp_block,
        encoding="utf-8",
    )

    for cache in (
        repo_root / ".cache" / "npm-cache",
        repo_root / ".cache" / "uv-cache",
        repo_root / ".cache" / "uv-tools",
    ):
        cache.mkdir(parents=True, exist_ok=True)

    gitignore = repo_root / ".gitignore"
    if gitignore.exists():
        text = gitignore.read_text(encoding="utf-8")
        if ".grok/config.toml" not in text:
            addition = (
                "\n# Grok machine-local MCP (absolute Windows paths)\n"
                ".grok/config.toml\n"
            )
            if not text.endswith("\n"):
                addition = "\n" + addition
            gitignore.write_text(text + addition, encoding="utf-8")

    return user_config, project_config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
        help="BioETL repository root",
    )
    parser.add_argument(
        "--user-config",
        type=Path,
        default=Path.home() / ".grok" / "config.toml",
        help="User-level Grok config path",
    )
    parser.add_argument(
        "--project-config",
        type=Path,
        default=None,
        help="Project .grok/config.toml (default: <repo>/.grok/config.toml)",
    )
    args = parser.parse_args(argv)
    repo_root = args.repo_root.resolve()
    project_config = (
        args.project_config.resolve()
        if args.project_config is not None
        else repo_root / ".grok" / "config.toml"
    )
    user_path, project_path = generate(
        repo_root=repo_root,
        user_config=args.user_config.resolve(),
        project_config=project_config,
    )
    print(f"wrote {user_path}")
    print(f"wrote {project_path}")
    print(f"core_enabled={sorted(CORE_ENABLED)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
