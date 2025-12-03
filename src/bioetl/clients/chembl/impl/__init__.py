"""ChEMBL-specific client implementations."""

from bioetl.clients.chembl.impl.chembl_normalization_service import (
    ChemblNormalizationServiceImpl,
)

__all__ = ["ChemblNormalizationServiceImpl"]
