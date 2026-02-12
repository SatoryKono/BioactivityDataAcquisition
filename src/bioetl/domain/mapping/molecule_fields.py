"""Mapping for molecule fields across different providers."""

MOLECULE_FIELD_MAPPING = {
    "chembl": {
        "logp": "logp",
        "hba_count": "hba_count",
        "molecular_weight": "molecular_weight",
    },
    "pubchem": {
        "xlogp": "logp",
        "hba": "hba_count",
        "molecular_weight": "molecular_weight",
    },
    # Add other providers here as needed (e.g., ZINC, etc.)
    # "zinc": {
    #     "logp": "logp", # Example
    # }
}
