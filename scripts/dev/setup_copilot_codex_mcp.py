#!/usr/bin/env python3
"""Canonical setup backend for Copilot/Codex GitHub MCP configuration."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

GITHUB_MCP_PACKAGE = "@modelcontextprotocol/server-github@2025.4.8"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Configure GitHub MCP for VS Code and Codex CLI."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Project root path",
    )
    parser.add_argument(
        "--skip-codex",
        action="store_true",
        help="Skip Codex MCP registration steps",
    )
    return parser


def _write_vscode_mcp(root: Path) -> None:
    vscode_mcp_path = root / ".vscode" / "mcp.json"
    print(f"[1/3] Writing VS Code MCP config: {vscode_mcp_path}")
    vscode_mcp_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "servers": {
            "github": {
                "command": "npx",
                "args": ["-y", GITHUB_MCP_PACKAGE],
            }
        }
    }
    vscode_mcp_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _codex_registration() -> int:
    codex_bin = shutil.which("codex")
    if codex_bin is None:
        print("[2/3] Codex CLI not found. Skipping Codex MCP registration.")
        print("[3/3] Done.")
        print("Set GITHUB_PERSONAL_ACCESS_TOKEN in your shell before using GitHub MCP tools.")
        return 0

    print("[2/3] Checking Codex MCP server registration: github")
    get_result = subprocess.run(
        [codex_bin, "mcp", "get", "github"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )

    if get_result.returncode == 0:
        print("      github MCP already registered in Codex.")
    else:
        add_result = subprocess.run(
            [codex_bin, "mcp", "add", "github", "--", "npx", "-y", GITHUB_MCP_PACKAGE],
            check=False,
        )
        if add_result.returncode != 0:
            print("[FAIL] Unable to register github MCP in Codex.")
            return add_result.returncode
        print("      github MCP registered in Codex.")

    print("[3/3] Done.")
    print("Set GITHUB_PERSONAL_ACCESS_TOKEN in your shell before using GitHub MCP tools.")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.root.resolve()
    _write_vscode_mcp(root)

    if args.skip_codex:
        print("[2/3] Skipping Codex MCP registration (requested).")
        print("[3/3] Done.")
        print("Set GITHUB_PERSONAL_ACCESS_TOKEN in your shell before using GitHub MCP tools.")
        return 0

    return _codex_registration()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
