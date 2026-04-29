"""Tooling entrypoints for memory refresh, validation, pruning, workflow, and note governance.

This package exposes submodules as attributes so callers can do:

    from memory.tooling import workflow

and access the module object. The original file declared names in __all__ but did
not import the submodules, which prevented attribute access (editor/test unresolved
references). Import the submodules explicitly and expose them via __all__.
"""

from __future__ import annotations

# Import submodules so they are available as attributes on the package. Tests and
# callers expect `memory.tooling.workflow` (module object) to be importable.
from . import (
    archive_note,
    create_note,
    promote_note,
    prune,
    refresh_all,
    review_curated,
    validate,
    workflow,
)

__all__ = [
    "archive_note",
    "create_note",
    "promote_note",
    "prune",
    "refresh_all",
    "review_curated",
    "validate",
    "workflow",
]
