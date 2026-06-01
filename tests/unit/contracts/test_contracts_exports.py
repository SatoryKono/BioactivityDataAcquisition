"""Tests for contracts package exports.

Verifies that the contracts package correctly exports all Gold schemas
from the canonical location (bioetl.domain.contracts).
"""

from __future__ import annotations

import pytest


@pytest.mark.unit
class TestContractsPackageExports:
    """Test that contracts package exports all required schemas."""

    def test_all_chembl_schemas_exported(self):
        """All ChEMBL Gold schemas should be importable from domain.contracts."""
        from bioetl.domain.contracts import (
            ChEMBLActivityGoldSchema,
            ChEMBLAssayGoldSchema,
            ChEMBLAssayParametersGoldSchema,
            ChEMBLCellLineGoldSchema,
            ChEMBLCompoundRecordGoldSchema,
            ChEMBLPublicationGoldSchema,
            ChEMBLPublicationSimilarityGoldSchema,
            ChEMBLPublicationTermGoldSchema,
            ChEMBLMoleculeGoldSchema,
            ChEMBLProteinClassGoldSchema,
            ChEMBLSubcellularFractionGoldSchema,
            ChEMBLTargetComponentGoldSchema,
            ChEMBLTargetGoldSchema,
            ChEMBLTargetProteinClassificationGoldSchema,
            ChEMBLTissueGoldSchema,
        )

        # Verify they are Pandera DataFrameModel classes
        assert hasattr(ChEMBLActivityGoldSchema, "validate")
        assert hasattr(ChEMBLAssayGoldSchema, "validate")
        assert hasattr(ChEMBLAssayParametersGoldSchema, "validate")
        assert hasattr(ChEMBLCellLineGoldSchema, "validate")
        assert hasattr(ChEMBLCompoundRecordGoldSchema, "validate")
        assert hasattr(ChEMBLPublicationGoldSchema, "validate")
        assert hasattr(ChEMBLPublicationSimilarityGoldSchema, "validate")
        assert hasattr(ChEMBLPublicationTermGoldSchema, "validate")
        assert hasattr(ChEMBLMoleculeGoldSchema, "validate")
        assert hasattr(ChEMBLProteinClassGoldSchema, "validate")
        assert hasattr(ChEMBLSubcellularFractionGoldSchema, "validate")
        assert hasattr(ChEMBLTargetComponentGoldSchema, "validate")
        assert hasattr(ChEMBLTargetGoldSchema, "validate")
        assert hasattr(ChEMBLTargetProteinClassificationGoldSchema, "validate")
        assert hasattr(ChEMBLTissueGoldSchema, "validate")

    def test_all_publication_schemas_exported(self):
        """All publication Gold schemas should be importable from domain.contracts."""
        from bioetl.domain.contracts import (
            CrossRefPublicationGoldSchema,
            OpenAlexPublicationGoldSchema,
            PubMedPublicationGoldSchema,
            SemanticScholarPublicationGoldSchema,
        )

        assert hasattr(CrossRefPublicationGoldSchema, "validate")
        assert hasattr(OpenAlexPublicationGoldSchema, "validate")
        assert hasattr(PubMedPublicationGoldSchema, "validate")
        assert hasattr(SemanticScholarPublicationGoldSchema, "validate")

    def test_composite_schemas_exported(self):
        """Composite Gold schemas should be importable from domain.contracts."""
        from bioetl.domain.contracts import (
            CompositeActivityGoldSchema,
            CompositeAssayGoldSchema,
            CompositeMoleculeGoldSchema,
            CompositePublicationGoldSchema,
            CompositeTargetGoldSchema,
        )

        assert hasattr(CompositeActivityGoldSchema, "validate")
        assert hasattr(CompositeAssayGoldSchema, "validate")
        assert hasattr(CompositeMoleculeGoldSchema, "validate")
        assert hasattr(CompositePublicationGoldSchema, "validate")
        assert hasattr(CompositeTargetGoldSchema, "validate")

    def test_pubchem_schema_exported(self):
        """PubChem Gold schema should be importable from domain.contracts."""
        from bioetl.domain.contracts import PubChemCompoundGoldSchema

        assert hasattr(PubChemCompoundGoldSchema, "validate")

    def test_uniprot_schemas_exported(self):
        """UniProt Gold schemas should be importable from domain.contracts."""
        from bioetl.domain.contracts import (
            UniProtIDMappingGoldSchema,
            UniProtProteinGoldSchema,
        )

        assert hasattr(UniProtIDMappingGoldSchema, "validate")
        assert hasattr(UniProtProteinGoldSchema, "validate")

    def test_date_regex_exported(self):
        """DATE_REGEX utility should be importable from domain.contracts."""
        from bioetl.domain.contracts import DATE_REGEX

        assert DATE_REGEX == r"^\d{4}-\d{2}-\d{2}$"


@pytest.mark.unit
class TestContractsSubmoduleImports:
    """Test that contracts submodules work correctly."""

    def test_import_from_gold_submodule(self):
        """Should be able to import from bioetl.domain.contracts.gold."""
        from bioetl.domain.contracts.gold import (
            ChEMBLActivityGoldSchema,
            PubChemCompoundGoldSchema,
        )

        assert hasattr(ChEMBLActivityGoldSchema, "validate")
        assert hasattr(PubChemCompoundGoldSchema, "validate")

    def test_import_from_provider_modules(self):
        """Should be able to import from provider-specific modules."""
        from bioetl.domain.contracts.gold.chembl import ChEMBLActivityGoldSchema
        from bioetl.domain.contracts.gold.pubchem import PubChemCompoundGoldSchema
        from bioetl.domain.contracts.gold.publications import (
            PubMedPublicationGoldSchema,
        )
        from bioetl.domain.contracts.gold.uniprot import UniProtProteinGoldSchema

        assert hasattr(ChEMBLActivityGoldSchema, "validate")
        assert hasattr(PubChemCompoundGoldSchema, "validate")
        assert hasattr(PubMedPublicationGoldSchema, "validate")
        assert hasattr(UniProtProteinGoldSchema, "validate")


@pytest.mark.unit
class TestSchemaAttributes:
    """Test that schemas have expected Pandera attributes."""

    def test_schema_has_strict_config(self):
        """All Gold schemas should have strict=True config."""
        from bioetl.domain.contracts import ChEMBLActivityGoldSchema

        # Pandera models have a Config class with strict attribute
        assert hasattr(ChEMBLActivityGoldSchema, "Config")
        assert getattr(ChEMBLActivityGoldSchema.Config, "strict", False) is True

    def test_schema_can_generate_json_schema(self):
        """Schemas should be able to generate JSON Schema."""
        from bioetl.domain.contracts import ChEMBLActivityGoldSchema

        # This method is used by generate_contracts.py
        assert hasattr(ChEMBLActivityGoldSchema, "to_json_schema")
