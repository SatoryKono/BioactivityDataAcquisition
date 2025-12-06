"""
Application-level entrypoint for ChEMBL extraction service.

Re-exports the infrastructure implementation to keep backward-compatible
imports for pipelines and tests.
"""

from bioetl.infrastructure.clients.chembl.impl.chembl_extraction_service_impl import (
    ChemblExtractionServiceImpl,
)

__all__ = ["ChemblExtractionServiceImpl"]

