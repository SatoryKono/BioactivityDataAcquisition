"""Mapping for activity fields across different providers.

Placeholder for cross-provider activity field unification.
ChEMBL activity uses canonical names directly; extend when adding
other providers (e.g., PubChem bioassay).
"""

from __future__ import annotations

ACTIVITY_FIELD_MAPPING: dict[str, dict[str, str]] = {
    "chembl": {},  # ChEMBL activity fields are already canonical
    # "pubchem": {...}  # Add when PubChem bioassay support is added
}
