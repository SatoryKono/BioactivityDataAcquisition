"""
Deprecated shim for domain extraction contracts.

The canonical definitions live in ``bioetl.domain.ports.extraction``.
"""

from bioetl.domain.ports.extraction import BatchAdapterABC, ExtractionServiceABC

__all__ = ["ExtractionServiceABC", "BatchAdapterABC"]
