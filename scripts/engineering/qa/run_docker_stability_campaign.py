#!/usr/bin/env python3
"""Run the resumable Docker stability promotion campaign."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

main = importlib.import_module(
    "scripts.engineering.qa.docker_stability_campaign.runner"
).main


if __name__ == "__main__":
    raise SystemExit(main())
