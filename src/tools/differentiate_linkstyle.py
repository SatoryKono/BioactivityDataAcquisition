"""Compatibility wrapper for ``scripts.diagrams.differentiate_linkstyle``.

The canonical diagram codemod lives under ``scripts/diagrams``. This module is
retained temporarily for existing direct invocations.
"""

from __future__ import annotations

from scripts.diagrams.differentiate_linkstyle import *
from scripts.diagrams.differentiate_linkstyle import (
    _ensure_path_within_root,
    _write_validated_mermaid_text,
    main,
)

if __name__ == "__main__":
    main()
