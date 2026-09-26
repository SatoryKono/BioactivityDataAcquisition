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

Storage assembly is imported lazily so metrics/tracing bootstrap can load
without importing StorageFactory (which resolves observability ports).
"""

from __future__ import annotations

from bioetl.composition.bootstrap.assembly.checkpoint import (
    bootstrap_checkpoint_adapter,
    bootstrap_composite_checkpoint_writer,
    bootstrap_quarantine_adapter,
)
from bioetl.composition.lazy_exports import install_lazy_exports

__all__ = [
    "bootstrap_checkpoint_adapter",
    "bootstrap_composite_checkpoint_writer",
    "bootstrap_quarantine_adapter",
    "bootstrap_storage_adapter",
]

install_lazy_exports(
    module_globals=globals(),
    public_exports={
        "bootstrap_storage_adapter": (
            "bioetl.composition.bootstrap.assembly.storage",
            "bootstrap_storage_adapter",
        ),
    },
    module_name=__name__,
    explicit_exports=__all__,
    cache=True,
)
