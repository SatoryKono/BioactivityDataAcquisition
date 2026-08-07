"""Compatibility wrapper for ``scripts.diagrams.fix.apply_elk_layout``.

The canonical diagram codemod lives under ``scripts/diagrams``. This module is
retained temporarily for existing direct invocations and architecture tests.

Deprecated: Use 'scripts.diagrams.fix.apply_elk_layout' instead.
This wrapper will be removed in a future version.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "src.tools.apply_elk_layout is deprecated. "
    "Use 'scripts.diagrams.fix.apply_elk_layout' instead.",
    DeprecationWarning,
    stacklevel=2
)

from scripts.diagrams.fix import apply_elk_layout as _apply_elk_layout

main = _apply_elk_layout.main

if __name__ == "__main__":
    main()
