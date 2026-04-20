#!/usr/bin/env python3
"""Compatibility shim for the historical ``scripts.ai.scripts.ai.code_quality_analysis`` path."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ai.code_quality_analysis import *  # noqa: F403
from scripts.ai.code_quality_analysis import main


if __name__ == "__main__":
    main()

    print("\n✅ Analysis complete!")
