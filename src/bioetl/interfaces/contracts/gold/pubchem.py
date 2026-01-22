"""PubChem Gold layer data contracts.

DEPRECATED: This module re-exports schemas from bioetl.domain.contracts.gold.pubchem for
backward compatibility. New code should import from bioetl.domain.contracts.gold.pubchem.

Contains Pandera DataFrameModel schemas for PubChem entities in the Gold layer:
- Compound: Chemical structures and identifiers from PubChem

Int→Float coercion note:
    Fields marked with `coerce=True` and `Series[float]` that are `int64` in Silver
    use float to handle nullable integers. This is a deliberate design decision
    documented in RULES.md §2.6.
"""

from __future__ import annotations

# Re-export all schemas from domain.contracts for backward compatibility
from bioetl.domain.contracts.gold.pubchem import PubChemCompoundGoldSchema

__all__ = ["PubChemCompoundGoldSchema"]
