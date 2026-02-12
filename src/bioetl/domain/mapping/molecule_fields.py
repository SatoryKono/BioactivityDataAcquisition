"""Mapping for molecule fields across different providers."""

MOLECULE_FIELD_MAPPING = {
    "chembl": {
        "property_alogp": "logp",
        "property_hba": "hba_count",
        "property_full_mwt": "molecular_weight",
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
