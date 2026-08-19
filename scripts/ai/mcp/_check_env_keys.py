#!/usr/bin/env python3
"""Report which MCP-related .env keys are set (lengths only)."""

from __future__ import annotations

from pathlib import Path


def load_dotenv(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.is_file():
        return env
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if key:
            env[key] = value
    return env


def main() -> None:
    env = load_dotenv(Path(".env"))
    keys = [
        "GITHUB_TOKEN",
        "GITHUB_PERSONAL_ACCESS_TOKEN",
        "BRAVE_API_KEY",
        "REF_TOOL_API_KEY",
        "CONTEXT7_API_KEY",
        "OPENROUTER_API_KEY",
        "OPENAI_API_KEY",
        "NEO4J_URI",
        "NEO4J_USERNAME",
        "NEO4J_PASSWORD",
        "NEO4J_AUTH",
        "HUB_PAT_TOKEN",
        "DOCKER_API_KEY",
        "NEEDLE_API_KEY",
        "GITHUB_ANY_PERSONAL_ACCESS_TOKEN",
        "GITHUB_CDX_PERSONAL_ACCESS_TOKEN",
    ]
    for key in keys:
        value = env.get(key, "")
        print(f"{key}: set={bool(value)} len={len(value)}")


if __name__ == "__main__":
    main()
