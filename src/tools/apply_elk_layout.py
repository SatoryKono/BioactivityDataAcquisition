"""Compatibility wrapper for ``scripts.diagrams.fix.apply_elk_layout``.

The canonical diagram codemod lives under ``scripts/diagrams``. This module is
retained temporarily for existing direct invocations and architecture tests.
"""

from __future__ import annotations

from scripts.diagrams import apply_elk_layout as _apply_elk_layout

main = _apply_elk_layout.main

if __name__ == "__main__":
    main()
