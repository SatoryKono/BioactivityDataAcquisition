"""ChEMBL client public exports."""

# Re-export commonly used implementation for test and user imports
from .impl.chembl_extraction_service_impl import ChemblExtractionServiceImpl

__all__ = [
    "ChemblExtractionServiceImpl",
]
