"""Compatibility wrapper for ``scripts.diagrams.apply_elk_layout``.

The canonical diagram codemod lives under ``scripts/diagrams``. This module is
retained temporarily for existing direct invocations and architecture tests.
"""

from __future__ import annotations

from scripts.diagrams.apply_elk_layout import *
from scripts.diagrams.apply_elk_layout import main

if __name__ == "__main__":
    main()
