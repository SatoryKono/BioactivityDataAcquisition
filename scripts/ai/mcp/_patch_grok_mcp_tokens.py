#!/usr/bin/env python3
"""Wire ref auth headers and bump MCP startup timeouts in Grok configs."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from scripts.engineering.common.repo_paths import REPO_ROOT, ensure_path_within_root


TIMEOUTS = {
    "adr-analysis": 300,
    "ast-grep": 180,
    "code-analyzer": 180,
    "context7": 180,
    "deja": 180,
    "docker": 180,
    "dockerhub": 180,
    "fetch": 180,
    "memory": 180,
    "mermaid": 180,
    "mutmut": 300,
    "neo4j-cypher": 180,
    "neo4j-memory": 180,
    "mcp-code-interpreter": 300,
    "brave-search": 180,
    "github": 180,
    "github-actions": 180,
}


def bump_timeouts(text: str) -> str:
    for name, sec in TIMEOUTS.items():
        pat = rf"(\[mcp_servers\.{re.escape(name)}\][\s\S]*?startup_timeout_sec\s*=\s*)\d+"
        text, _n = re.subn(pat, rf"\g<1>{sec}", text, count=1)
    return text


def wire_ref(text: str) -> str:
    if "x-ref-api-key" in text and "REF_TOOL_API_KEY" in text:
        return text
    pattern = re.compile(
        r"(\[mcp_servers\.ref\]\s*\n"
        r"enabled\s*=\s*true\s*\n"
        r'url\s*=\s*"https://api\.ref\.tools/mcp"\s*\n'
        r"startup_timeout_sec\s*=\s*\d+\s*\n)"
    )
    replacement = (
        r"\1"
        r'headers = { "x-ref-api-key" = "${REF_TOOL_API_KEY}" }\n'
    )
    new_text, n = pattern.subn(replacement, text, count=1)
    if n:
        return new_text
    # Single-quoted url variant
    pattern2 = re.compile(
        r"(\[mcp_servers\.ref\]\s*\n"
        r"enabled\s*=\s*true\s*\n"
        r"url\s*=\s*'https://api\.ref\.tools/mcp'\s*\n"
        r"startup_timeout_sec\s*=\s*\d+\s*\n)"
    )
    replacement2 = (
        r"\1"
        r"headers = { \"x-ref-api-key\" = \"${REF_TOOL_API_KEY}\" }\n"
    )
    new_text, n = pattern2.subn(replacement2, text, count=1)
    return new_text if n else text


def _trusted_config_targets(
    *,
    include_home: bool,
    repo_root: Path,
    home: Path,
) -> tuple[tuple[Path, Path], ...]:
    """Return config paths paired with their explicit trust roots."""
    safe_repo_root = repo_root.resolve()
    project_grok_root = ensure_path_within_root(
        safe_repo_root / ".grok",
        safe_repo_root,
    )
    targets = [
        (
            ensure_path_within_root(
                project_grok_root / "config.toml",
                project_grok_root,
            ),
            project_grok_root,
        )
    ]
    if include_home:
        safe_home = home.resolve()
        home_grok_root = ensure_path_within_root(safe_home / ".grok", safe_home)
        targets.append(
            (
                ensure_path_within_root(
                    home_grok_root / "config.toml",
                    home_grok_root,
                ),
                home_grok_root,
            )
        )
    return tuple(targets)


def main(
    argv: list[str] | None = None,
    *,
    repo_root: Path | None = None,
    home: Path | None = None,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write patched configs. Default is check-only.",
    )
    parser.add_argument(
        "--include-home",
        action="store_true",
        help="Also consider Path.home() / .grok / config.toml (requires --apply to write).",
    )
    args = parser.parse_args(argv)
    targets = _trusted_config_targets(
        include_home=args.include_home,
        repo_root=repo_root or REPO_ROOT,
        home=home or Path.home(),
    )
    for candidate, allowed_root in targets:
        safe_path = ensure_path_within_root(candidate, allowed_root)
        if not safe_path.is_file():
            print("missing", safe_path)
            continue
        original = safe_path.read_text(encoding="utf-8")
        updated = bump_timeouts(wire_ref(original))
        if updated != original:
            if args.apply:
                safe_path.write_text(  # NOSONAR - target is confined above
                    updated,
                    encoding="utf-8",
                    newline="\n",
                )
                print("updated", safe_path)
            else:
                print("would-update", safe_path)
        else:
            print("unchanged", safe_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
