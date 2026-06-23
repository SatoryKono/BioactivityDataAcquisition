"""Assembly module for shared bootstrap infrastructure.

Contains bootstrap functions for infrastructure components that are used by
both CLI and runtime contexts. These functions have no side-effects and
create pure infrastructure adapters.

Components:
- checkpoint: Checkpoint and quarantine port creation
- storage: Storage adapter assembly for I/O operations

Note:
    This module should NOT contain any NoOp implementations or CLI-specific
    logic. It provides neutral building blocks for higher-level bootstrap.
"""

from __future__ import annotations

from bioetl.composition.bootstrap.assembly.checkpoint import (
    bootstrap_checkpoint_adapter,
    bootstrap_composite_checkpoint_writer,
    bootstrap_quarantine_adapter,
)
from bioetl.composition.bootstrap.assembly.storage import (
    bootstrap_storage_adapter,
)

__all__ = [
    "bootstrap_checkpoint_adapter",
    "bootstrap_composite_checkpoint_writer",
    "bootstrap_quarantine_adapter",
    "bootstrap_storage_adapter",
]
