#!/usr/bin/env python3
"""Deprecated compatibility entrypoint for canonical Codex skill validation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ai.codex.native_runtime_contract import validate_canonical_skills


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate canonical project skills (the only supported behavior).",
    )
    parser.parse_args()
    errors = validate_canonical_skills(REPO_ROOT)
    for error in errors:
        print(f"[FAIL] {error}")
    if errors:
        return 1
    print(
        "[OK] compatibility entrypoint is read-only; canonical Codex skills are valid"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
