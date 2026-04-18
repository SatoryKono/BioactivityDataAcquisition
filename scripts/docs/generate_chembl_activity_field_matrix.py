#!/usr/bin/env python3
"""Compatibility shim for the packaged ChEMBL activity field-matrix generator."""

from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

_IMPL = import_module("scripts.docs.matrix.generate_field_matrix")
globals().update(
    {
        name: value
        for name, value in vars(_IMPL).items()
        if name not in {"__name__", "__package__", "__loader__", "__spec__"}
    }
)


if __name__ == "__main__":
    raise SystemExit(main())
