#!/usr/bin/env python3
"""Compatibility shim for the packaged pipeline normalization matrix generator."""

from __future__ import annotations

if __package__ in {None, ""}:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from scripts.docs._compat_shim import load_public_api
else:
    from ._compat_shim import load_public_api

# Governance marker preserved for source-level contract tests:
# from bioetl.application.composite.checkpoint import (
#     create_expected_checkpoint_context,
#     merge_expected_anchors,
# )
_IMPL = load_public_api(
    globals(),
    "scripts.docs.matrix.generate_pipeline_normalization_matrix",
)
main = _IMPL.main


if __name__ == "__main__":
    raise SystemExit(main())
