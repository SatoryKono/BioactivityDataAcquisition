#!/usr/bin/env python3
"""Render diagrams from Mermaid files.

This script processes Mermaid diagram files in the docs directory
and ensures they are properly formatted and valid.

Currently a placeholder that validates diagram file existence.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Configure logging for CLI output
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def find_mermaid_files(docs_dir: Path) -> list[Path]:
    """Find all Mermaid diagram files in docs."""
    return list(docs_dir.rglob("*.mmd")) + list(docs_dir.rglob("*.mermaid"))


def validate_diagrams(docs_dir: Path) -> bool:
    """Validate that diagram files exist and are readable."""
    mermaid_files = find_mermaid_files(docs_dir)

    if not mermaid_files:
        logger.info("No Mermaid diagram files found in docs/")
        return True

    logger.info("Found %d Mermaid diagram file(s):", len(mermaid_files))
    for f in mermaid_files:
        logger.info("  - %s", f.relative_to(docs_dir.parent))

    return True


def main() -> int:
    """Main entry point."""
    project_root = Path(__file__).parent.parent.parent
    docs_dir = project_root / "docs"

    if not docs_dir.exists():
        logger.warning("Warning: docs directory not found at %s", docs_dir)
        return 0

    if validate_diagrams(docs_dir):
        logger.info("Diagram validation passed.")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
