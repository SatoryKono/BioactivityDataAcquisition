"""PubChem API contract tests.

Verifies that PubChem PUG REST API endpoints and response schemas haven't changed.
These tests make live API calls and require BIOETL_LIVE_API_TESTS=true.

See:
    - https://pubchemdocs.ncbi.nlm.nih.gov/pug-rest
    - RULES.md Appendix A - PubChem specifications
"""

from __future__ import annotations

import httpx
import pytest

PUBCHEM_API_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
pytestmark = pytest.mark.network


@pytest.mark.pubchem
class TestPubChemContract:
    """Contract tests for PubChem PUG REST API."""

    @pytest.mark.asyncio
    async def test_compound_by_molecule_id(self) -> None:
        """Verify compound lookup by CID."""
        molecule_id = 2244  # Aspirin

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{PUBCHEM_API_BASE}/compound/molecule_id/{molecule_id}/JSON",
            )

        assert response.status_code == 200
        data = response.json()

        # PubChem nests data under PC_Compounds
        assert "PC_Compounds" in data
        compounds = data["PC_Compounds"]
        assert len(compounds) >= 1

        compound = compounds[0]
        # Compound should have id with molecule_id
        assert "id" in compound
        assert compound["id"]["id"]["molecule_id"] == molecule_id

    @pytest.mark.asyncio
    async def test_compound_by_name(self) -> None:
        """Verify compound search by name."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{PUBCHEM_API_BASE}/compound/name/aspirin/JSON",
            )

        assert response.status_code == 200
        data = response.json()

        assert "PC_Compounds" in data
        assert len(data["PC_Compounds"]) >= 1

    @pytest.mark.asyncio
    async def test_compound_property_endpoint(self) -> None:
        """Verify property retrieval endpoint."""
        molecule_id = 2244  # Aspirin

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{PUBCHEM_API_BASE}/compound/molecule_id/{molecule_id}/property/"
                "MolecularFormula,MolecularWeight,CanonicalSMILES/JSON",
            )

        assert response.status_code == 200
        data = response.json()

        assert "PropertyTable" in data
        assert "Properties" in data["PropertyTable"]

        props = data["PropertyTable"]["Properties"][0]
        assert "CID" in props
        assert "MolecularFormula" in props
        assert "MolecularWeight" in props
        # API may return CanonicalSMILES or ConnectivitySMILES depending on request
        assert "CanonicalSMILES" in props or "ConnectivitySMILES" in props

    @pytest.mark.asyncio
    async def test_substance_endpoint(self) -> None:
        """Verify substance endpoint schema."""
        sid = 144204857  # Known stable substance ID

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{PUBCHEM_API_BASE}/substance/sid/{sid}/JSON",
            )

        # May return 200 or 404 if substance was retired
        if response.status_code == 200:
            data = response.json()
            assert "PC_Substances" in data

    @pytest.mark.asyncio
    async def test_assay_endpoint(self) -> None:
        """Verify bioassay endpoint schema."""
        aid = 504466  # Known stable bioassay (Tox21)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{PUBCHEM_API_BASE}/assay/aid/{aid}/JSON",
            )

        # Assay endpoint may return 400 if assay is retired or invalid
        if response.status_code == 200:
            data = response.json()
            assert "PC_AssaySubmit" in data
        else:
            # Accept 400/404 for deprecated assays
            assert response.status_code in (400, 404)

    @pytest.mark.asyncio
    async def test_molecule_id_list_endpoint(self) -> None:
        """Verify multiple CID retrieval."""
        molecule_ids = [2244, 3672]  # Aspirin, Ibuprofen

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{PUBCHEM_API_BASE}/compound/molecule_id/property/MolecularFormula/JSON",
                data={"molecule_id": ",".join(map(str, molecule_ids))},
            )

        assert response.status_code == 200
        data = response.json()

        assert "PropertyTable" in data
        props = data["PropertyTable"]["Properties"]
        assert len(props) == 2

    @pytest.mark.asyncio
    async def test_smiles_search(self) -> None:
        """Verify SMILES-based structure search."""
        smiles = "CC(=O)OC1=CC=CC=C1C(=O)O"  # Aspirin

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{PUBCHEM_API_BASE}/compound/smiles/{smiles}/molecule_ids/JSON",
            )

        assert response.status_code == 200
        data = response.json()

        assert "IdentifierList" in data
        assert "CID" in data["IdentifierList"]
        # Aspirin should be found
        assert 2244 in data["IdentifierList"]["CID"]

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_similarity_search(self) -> None:
        """Verify similarity search endpoint."""
        molecule_id = 2244  # Aspirin

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                f"{PUBCHEM_API_BASE}/compound/fastsimilarity_2d/molecule_id/{molecule_id}/molecule_ids/JSON",
                params={"Threshold": 95},
            )

        # Similarity search may take time
        assert response.status_code in (200, 202)  # 202 = accepted, processing
