"""UniProt Gold layer data contracts.

DEPRECATED: This module re-exports schemas from bioetl.domain.contracts.gold.uniprot for
backward compatibility. New code should import from bioetl.domain.contracts.gold.uniprot.

Contains Pandera DataFrameModel schemas for UniProt entities in the Gold layer:
- Protein: UniProt protein sequences and metadata
- IDMapping: ChEMBL→UniProt target ID mappings with status tracking

Int→Float coercion note:
    Fields marked with `coerce=True` and `Series[float]` that are `int64` in Silver
    use float to handle nullable integers. This is a deliberate design decision
    documented in RULES.md §2.6.
"""

from __future__ import annotations

# Re-export all schemas from domain.contracts for backward compatibility
from bioetl.domain.contracts.gold.uniprot import (
    UniProtIDMappingGoldSchema,
    UniProtProteinGoldSchema,
)

__all__ = [
    "UniProtIDMappingGoldSchema",
    "UniProtProteinGoldSchema",
]
