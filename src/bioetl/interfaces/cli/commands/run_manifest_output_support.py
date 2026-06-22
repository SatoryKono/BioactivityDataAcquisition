"""Public CLI text-output helpers for cross-domain command rendering.

This facade lets domain-scoped command modules reuse stable run-manifest text
formatting primitives without importing the private owner-local implementation
module directly.
"""

from __future__ import annotations

from bioetl.interfaces.cli.commands._run_manifest_output_support import (
    append_section,
    format_scalar,
    render_manifest_section,
)

__all__ = [
    "append_section",
    "format_scalar",
    "render_manifest_section",
]
