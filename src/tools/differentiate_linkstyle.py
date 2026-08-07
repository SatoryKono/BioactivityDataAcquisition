"""Compatibility wrapper for ``scripts.diagrams.fix.differentiate_linkstyle``.

The canonical diagram codemod lives under ``scripts/diagrams``. This module is
retained temporarily for existing direct invocations.
"""

from __future__ import annotations

from scripts.diagrams.fix import differentiate_linkstyle as _differentiate_linkstyle

# Re-export security-relevant symbols so direct wrappers stay patchable in tests.
MERMAID_DIR = _differentiate_linkstyle.MERMAID_DIR
_ensure_path_within_root = _differentiate_linkstyle._ensure_path_within_root
_write_validated_mermaid_text = _differentiate_linkstyle._write_validated_mermaid_text
main = _differentiate_linkstyle.main

if __name__ == "__main__":
    main()
