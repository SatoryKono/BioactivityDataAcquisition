"""Query builder helpers for PubChem fetch endpoints."""

from __future__ import annotations

from urllib.parse import quote

__all__ = [
    "build_assay_endpoint",
    "build_cid_batch_endpoint",
    "build_compound_name_endpoint",
    "build_inchikey_endpoint",
    "build_smiles_endpoint",
    "build_substance_name_endpoint",
]


def _encode_path_value(query: str) -> str:
    return quote(query, safe="")


def build_compound_name_endpoint(query: str) -> str:
    """Build endpoint for compound name search."""
    return f"/compound/name/{_encode_path_value(query)}/JSON"


def build_substance_name_endpoint(query: str) -> str:
    """Build endpoint for substance name search."""
    return f"/substance/name/{_encode_path_value(query)}/JSON"


def build_assay_endpoint(query: str) -> str:
    """Build endpoint for assay lookup."""
    return f"/assay/aid/{_encode_path_value(query)}/JSON"


def build_smiles_endpoint() -> str:
    """Build endpoint for SMILES structure lookup."""
    return "/compound/smiles/JSON"


def build_inchikey_endpoint() -> str:
    """Build endpoint for InChIKey structure lookup."""
    return "/compound/inchikey/JSON"


def build_cid_batch_endpoint(batch: list[int]) -> str:
    """Build endpoint for CID batch lookup."""
    if not batch:
        raise ValueError("CID batch must contain at least one CID")
    joined = ",".join(map(str, batch))
    return f"/compound/cid/{joined}/JSON"
