"""Tests for contracts package exports.

Verifies that the contracts package correctly exports all Gold schemas
and provides backward-compatible imports.
"""

from __future__ import annotations

import pytest


@pytest.mark.unit
class TestContractsPackageExports:
    """Test that contracts package exports all required schemas."""

    def test_all_chembl_schemas_exported(self):
        """All ChEMBL Gold schemas should be importable from contracts."""
        from bioetl.contracts import (
            ChEMBLActivityGoldSchema,
            ChEMBLAssayGoldSchema,
            ChEMBLAssayParametersGoldSchema,
            ChEMBLCellLineGoldSchema,
            ChEMBLCompoundRecordGoldSchema,
            ChEMBLDocumentGoldSchema,
            ChEMBLDocumentSimilarityGoldSchema,
            ChEMBLDocumentTermGoldSchema,
            ChEMBLMoleculeGoldSchema,
            ChEMBLProteinClassGoldSchema,
            ChEMBLTargetComponentGoldSchema,
            ChEMBLTargetGoldSchema,
        )

        # Verify they are Pandera DataFrameModel classes
        assert hasattr(ChEMBLActivityGoldSchema, "validate")
        assert hasattr(ChEMBLAssayGoldSchema, "validate")
        assert hasattr(ChEMBLAssayParametersGoldSchema, "validate")
        assert hasattr(ChEMBLCellLineGoldSchema, "validate")
        assert hasattr(ChEMBLCompoundRecordGoldSchema, "validate")
        assert hasattr(ChEMBLDocumentGoldSchema, "validate")
        assert hasattr(ChEMBLDocumentSimilarityGoldSchema, "validate")
        assert hasattr(ChEMBLDocumentTermGoldSchema, "validate")
        assert hasattr(ChEMBLMoleculeGoldSchema, "validate")
        assert hasattr(ChEMBLProteinClassGoldSchema, "validate")
        assert hasattr(ChEMBLTargetComponentGoldSchema, "validate")
        assert hasattr(ChEMBLTargetGoldSchema, "validate")

    def test_all_publication_schemas_exported(self):
        """All publication Gold schemas should be importable from contracts."""
        from bioetl.contracts import (
            CrossRefPublicationGoldSchema,
            OpenAlexPublicationGoldSchema,
            PubMedPublicationGoldSchema,
            SemanticScholarPublicationGoldSchema,
        )

        assert hasattr(CrossRefPublicationGoldSchema, "validate")
        assert hasattr(OpenAlexPublicationGoldSchema, "validate")
        assert hasattr(PubMedPublicationGoldSchema, "validate")
        assert hasattr(SemanticScholarPublicationGoldSchema, "validate")

    def test_pubchem_schema_exported(self):
        """PubChem Gold schema should be importable from contracts."""
        from bioetl.contracts import PubChemCompoundGoldSchema

        assert hasattr(PubChemCompoundGoldSchema, "validate")

    def test_uniprot_schemas_exported(self):
        """UniProt Gold schemas should be importable from contracts."""
        from bioetl.contracts import (
            UniProtIDMappingGoldSchema,
            UniProtProteinGoldSchema,
        )

        assert hasattr(UniProtIDMappingGoldSchema, "validate")
        assert hasattr(UniProtProteinGoldSchema, "validate")

    def test_date_regex_exported(self):
        """DATE_REGEX utility should be importable from contracts."""
        from bioetl.contracts import DATE_REGEX

        assert DATE_REGEX == r"^\d{4}-\d{2}-\d{2}$"


@pytest.mark.unit
class TestContractsSubmoduleImports:
    """Test that contracts submodules work correctly."""

    def test_import_from_gold_submodule(self):
        """Should be able to import from bioetl.contracts.gold."""
        from bioetl.contracts.gold import (
            ChEMBLActivityGoldSchema,
            PubChemCompoundGoldSchema,
        )

        assert hasattr(ChEMBLActivityGoldSchema, "validate")
        assert hasattr(PubChemCompoundGoldSchema, "validate")

    def test_import_from_provider_modules(self):
        """Should be able to import from provider-specific modules."""
        from bioetl.contracts.gold.chembl import ChEMBLActivityGoldSchema
        from bioetl.contracts.gold.pubchem import PubChemCompoundGoldSchema
        from bioetl.contracts.gold.publications import PubMedPublicationGoldSchema
        from bioetl.contracts.gold.uniprot import UniProtProteinGoldSchema

        assert hasattr(ChEMBLActivityGoldSchema, "validate")
        assert hasattr(PubChemCompoundGoldSchema, "validate")
        assert hasattr(PubMedPublicationGoldSchema, "validate")
        assert hasattr(UniProtProteinGoldSchema, "validate")


@pytest.mark.unit
class TestBackwardCompatibility:
    """Test backward compatibility with old import paths."""

    def test_old_import_path_still_works(self):
        """Old import path should still work for backward compatibility."""
        # This should work because infrastructure.schemas.gold re-exports
        # from contracts
        from bioetl.infrastructure.schemas.gold import (
            ChEMBLActivityGoldSchema,
            PubChemCompoundGoldSchema,
        )

        assert hasattr(ChEMBLActivityGoldSchema, "validate")
        assert hasattr(PubChemCompoundGoldSchema, "validate")

    def test_date_regex_backward_compatible(self):
        """DATE_REGEX should be accessible from old path."""
        from bioetl.infrastructure.schemas.gold import DATE_REGEX

        assert DATE_REGEX == r"^\d{4}-\d{2}-\d{2}$"

    def test_schemas_are_identical(self):
        """Schemas from both paths should be the same object."""
        from bioetl.contracts import ChEMBLActivityGoldSchema as NewSchema
        from bioetl.infrastructure.schemas.gold import (
            ChEMBLActivityGoldSchema as OldSchema,
        )

        assert NewSchema is OldSchema


@pytest.mark.unit
class TestSchemaAttributes:
    """Test that schemas have expected Pandera attributes."""

    def test_schema_has_strict_config(self):
        """All Gold schemas should have strict=True config."""
        from bioetl.contracts import ChEMBLActivityGoldSchema

        # Pandera models have a Config class with strict attribute
        assert hasattr(ChEMBLActivityGoldSchema, "Config")
        assert getattr(ChEMBLActivityGoldSchema.Config, "strict", False) is True

    def test_schema_can_generate_json_schema(self):
        """Schemas should be able to generate JSON Schema."""
        from bioetl.contracts import ChEMBLActivityGoldSchema

        # This method is used by generate_contracts.py
        assert hasattr(ChEMBLActivityGoldSchema, "to_json_schema")
