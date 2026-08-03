"""Compatibility wrapper for ``scripts.diagrams.harmonize_link_styles``.

The canonical diagram codemod lives under ``scripts/diagrams``. This module is
retained temporarily for existing direct invocations.
"""

from __future__ import annotations

from scripts.diagrams import harmonize_link_styles as _harmonize_link_styles

main = _harmonize_link_styles.main

if __name__ == "__main__":
    raise SystemExit(main())
