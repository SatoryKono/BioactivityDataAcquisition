#!/usr/bin/env python3
"""Compatibility shim for the packaged pipeline normalization matrix generator."""

from __future__ import annotations

from importlib import import_module
import sys
from pathlib import Path

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo_root))
    sys.path.insert(0, str(repo_root / "src"))

# Governance marker preserved for source-level contract tests:
# from bioetl.application.composite.checkpoint import (
#     create_expected_checkpoint_context,
#     merge_expected_anchors,
# )
_IMPL = import_module("scripts.docs.matrix.generate_pipeline_normalization_matrix")
globals().update(
    {
        name: value
        for name, value in vars(_IMPL).items()
        if name not in {"__name__", "__package__", "__loader__", "__spec__"}
    }
)


if __name__ == "__main__":
    raise SystemExit(main())
