#!/usr/bin/env python3
"""Wire ref auth headers and bump MCP startup timeouts in Grok configs."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


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


def main(argv: list[str] | None = None) -> int:
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
    paths = [Path(".grok/config.toml")]
    if args.include_home:
        paths.append(Path.home() / ".grok" / "config.toml")
    for path in paths:
        if not path.is_file():
            print("missing", path)
            continue
        original = path.read_text(encoding="utf-8")
        updated = bump_timeouts(wire_ref(original))
        if updated != original:
            if args.apply:
                path.write_text(updated, encoding="utf-8", newline="\n")
                print("updated", path)
            else:
                print("would-update", path)
        else:
            print("unchanged", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
