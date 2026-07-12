"""Compatibility wrapper for ``scripts.diagrams.differentiate_linkstyle``.

The canonical diagram codemod lives under ``scripts/diagrams``. This module is
retained temporarily for existing direct invocations.
"""

from __future__ import annotations

from scripts.diagrams.differentiate_linkstyle import *  # noqa: F403
from scripts.diagrams.differentiate_linkstyle import main

if __name__ == "__main__":
    main()
