"""Domain contracts for output operations.

This module defines abstract interfaces for file writing operations,
including deterministic and atomic write semantics.
"""

from bioetl.domain.output.deterministic import (
    DeterministicWriterABC,
    DeterministicWriteResult,
)

__all__ = [
    "DeterministicWriterABC",
    "DeterministicWriteResult",
]
