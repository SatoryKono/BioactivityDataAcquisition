#!/usr/bin/env python3
"""Compatibility shim for the packaged MkDocs build entrypoint."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Add the repository root to sys.path for mkdocs to find its config
repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from mkdocs.commands import build
from mkdocs.config import load_config


def main() -> int:
    parser = argparse.ArgumentParser(description="Run MkDocs build with specific options.")
    parser.add_argument("--strict", action="store_true", help="Enable strict mode.")
    parser.add_argument("--clean", action="store_true", help="Remove old files from the site_dir before building.")
    parser.add_argument("--site-dir", type=str, default="site", help="The directory to build the docs to.")
    
    # MkDocs build expects sys.argv to be ['mkdocs', 'build', ...]
    # We need to simulate this for proper argument parsing within mkdocs build if we were to call it directly.
    # However, since we're using build.build(config_options), we directly pass the options.
    args = parser.parse_args()

    # Load MkDocs configuration
    config = load_config(
        config_file="mkdocs.yml",
        strict=args.strict,
        site_dir=args.site_dir,
    )

    # Apply clean flag manually, as it's typically handled by the CLI entrypoint
    # For build.build(), the 'clean' argument is explicit.
    config['clean'] = args.clean

    try:
        build.build(config)
        print(f"MkDocs site generated at {args.site_dir}")
        return 0
    except Exception as e: # Catch all exceptions
        print(f"Error building MkDocs site: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
