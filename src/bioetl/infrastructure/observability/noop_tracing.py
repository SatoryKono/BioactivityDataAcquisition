"""Re-export NoOpTracing from domain ports (canonical definition).

The canonical NoOpTracing implementation lives in ``bioetl.domain.ports.noop``.
This module re-exports it so that existing infrastructure consumers continue
to work without import path changes.
"""

from bioetl.domain.ports import NoOpTracing

__all__ = ["NoOpTracing"]
