#!/usr/bin/env python3
"""Compatibility shim for the historical ``scripts.ai.src.sonarqube_mcp_smoke`` path."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ai.mcp.sonarqube_mcp_smoke import *  # noqa: F403
from scripts.ai.mcp.sonarqube_mcp_smoke import main


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
