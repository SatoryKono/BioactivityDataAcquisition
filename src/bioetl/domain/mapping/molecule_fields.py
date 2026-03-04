"""Mapping for molecule fields across different providers."""

from __future__ import annotations

__all__ = [
    "MOLECULE_FIELD_MAPPING",
]


MOLECULE_FIELD_MAPPING = {
    "chembl": {
        "logp": "logp",
        "hba_count": "hba_count",
        "molecular_weight": "molecular_weight",
        "inchi_key": "inchi_key",
    },
    "pubchem": {
        "xlogp": "logp",
        "hba": "hba_count",
        "molecular_weight": "molecular_weight",
        "inchi_key": "inchi_key",
    },
    # Add other providers here as needed (e.g., ZINC, etc.)
    # "zinc": {
    #     "logp": "logp", # Example
    # }
}
