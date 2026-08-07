"""Compatibility wrapper for ``scripts.diagrams.fix.harmonize_link_styles``.

The canonical diagram codemod lives under ``scripts/diagrams``. This module is
retained temporarily for existing direct invocations.

Deprecated: Use 'scripts.diagrams.fix.harmonize_link_styles' instead.
This wrapper will be removed in a future version.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "src.tools.harmonize_link_styles is deprecated. "
    "Use 'scripts.diagrams.fix.harmonize_link_styles' instead.",
    DeprecationWarning,
    stacklevel=2
)

from scripts.diagrams.fix import harmonize_link_styles as _harmonize_link_styles

main = _harmonize_link_styles.main

if __name__ == "__main__":
    raise SystemExit(main())
