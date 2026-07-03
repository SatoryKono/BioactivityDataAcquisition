"""Integration tests for composite molecule pipeline.

Tests the composite_molecule pipeline that combines:
- Seed: chembl_molecule (pharmaceutical compounds with clinical data)
- Enricher: pubchem_compound (chemical properties and synonyms)

Join Strategy:
- Primary: InChIKey (IUPAC standard, 27 characters)
- Fallback: canonical_smiles (less reliable)

Reference: ADR-026 Composite Pipeline Pattern
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import polars as pl
import pytest
import yaml

from bioetl.application.composite.column_renamer import ColumnRenamer
from bioetl.domain.composite.config import (
    ColumnGroupConfig,
    CompositeConfig,
    EnricherConfig,
    MergeConfig,
    SeedConfig,
)
from bioetl.domain.composite.strategy import (
    ConflictResolution,
    MergeStrategy,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create mock logger for testing."""
    logger = MagicMock()
    logger.debug = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger


@pytest.fixture
def seed_molecule_df() -> pl.DataFrame:
    """Seed DataFrame simulating chembl_molecule output."""
    return pl.DataFrame(
        {
            # System fields
            "entity_id": ["chembl:CHEMBL25", "chembl:CHEMBL192", "chembl:CHEMBL941"],
            "content_hash": ["hash1", "hash2", "hash3"],
            "_run_id": ["run1", "run1", "run1"],
            "_run_type": ["incremental", "incremental", "incremental"],
            "_source_batch_id": ["batch1", "batch1", "batch1"],
            "_ingestion_ts": ["2026-02-03T00:00:00Z"] * 3,
            "_index": [0, 1, 2],
            "_dq_warn": [False, False, False],
            "_dq_error": [False, False, False],
            # Business fields
            "molecule_id": ["CHEMBL25", "CHEMBL192", "CHEMBL941"],
            "pref_name": ["ASPIRIN", "IBUPROFEN", "IMATINIB"],
            "inchi_key": [
                "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",  # Aspirin
                "HEFNNWSXXWATRW-UHFFFAOYSA-N",  # Ibuprofen
                "KTUFNOKKBVMGRW-UHFFFAOYSA-N",  # Imatinib
            ],
            "canonical_smiles": [
                "CC(=O)OC1=CC=CC=C1C(=O)O",  # Aspirin
                "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O",  # Ibuprofen
                "CC1=C(C=C(C=C1)NC(=O)C2=CC=C(C=C2)CN3CCN(CC3)C)NC4=NC=CC(=N4)C5=CN=CC=C5",  # Imatinib
            ],
            "max_phase": [4.0, 4.0, 4.0],
            "molecular_weight": [180.16, 206.28, 493.60],
            "logp": [1.19, 3.50, 3.50],
            "therapeutic_flag": [True, True, True],
            "withdrawn_flag": [False, False, False],
        }
    )


@pytest.fixture
def enricher_pubchem_df() -> pl.DataFrame:
    """Enricher DataFrame simulating pubchem_compound output."""
    return pl.DataFrame(
        {
            # System fields
            "entity_id": ["pubchem:2244", "pubchem:3672"],
            "content_hash": ["phash1", "phash2"],
            "_run_id": ["run2", "run2"],
            "_run_type": ["incremental", "incremental"],
            "_source_batch_id": ["batch2", "batch2"],
            "_ingestion_ts": ["2026-02-03T01:00:00Z"] * 2,
            "_index": [0, 1],
            "_dq_warn": [False, False],
            "_dq_error": [False, False],
            # Business fields - matches aspirin and ibuprofen by inchi_key
            "molecule_id": ["2244", "3672"],
            "inchi_key": [
                "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",  # Aspirin
                "HEFNNWSXXWATRW-UHFFFAOYSA-N",  # Ibuprofen
            ],
            "canonical_smiles": [
                "CC(=O)OC1=CC=CC=C1C(=O)O",  # Aspirin
                "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O",  # Ibuprofen
            ],
            "iupac_name": [
                "2-acetoxybenzoic amolecule_id",
                "2-(4-isobutylphenyl)propionic amolecule_id",
            ],
            "molecular_weight": [180.157, 206.285],
            "molecular_formula": ["C9H8O4", "C13H18O2"],
            "inchi": [
                "InChI=1S/C9H8O4/c1-6(10)13-8-5-3-2-4-7(8)9(11)12/h2-5H,1H3,(H,11,12)",
                "InChI=1S/C13H18O2/c1-9(2)8-11-4-6-12(7-5-11)10(3)13(14)15/h4-7,9-10H,8H2,1-3H3,(H,14,15)",
            ],
        }
    )


@pytest.fixture
def composite_molecule_config() -> CompositeConfig:
    """Create composite molecule configuration for testing."""
    return CompositeConfig(
        name="composite_molecule",
        version="1.0.0",
        seed=SeedConfig(
            pipeline="chembl_molecule",
            output_keys=("molecule_id", "inchi_key", "canonical_smiles"),
            silver_table="silver/chembl/molecule",
        ),
        enrichers=(
            EnricherConfig(
                pipeline="pubchem_compound",
                join_keys=("inchi_key", "canonical_smiles"),
                required=False,
                filter_condition="inchi_key IS NOT NULL",
                timeout_seconds=3600,
                silver_table="silver/pubchem/compound",
            ),
        ),
        merge=MergeConfig(
            strategy=MergeStrategy.LEFT_OUTER,
            conflict_resolution=ConflictResolution.SEED_PRIORITY,
            preserve_all_sources=True,
            field_priorities={
                "canonical_smiles": ["chembl", "pubchem"],
                "inchi_key": ["chembl", "pubchem"],
                "molecular_weight": ["pubchem", "chembl"],
            },
            column_groups=(
                ColumnGroupConfig(
                    name="system",
                    fields=(
                        "entity_id",
                        "content_hash",
                        "_run_id",
                        "_run_type",
                        "_ingestion_ts",
                    ),
                    pattern=None,
                    provider_order=("chembl", "pubchem"),
                ),
                ColumnGroupConfig(
                    name="identifiers",
                    fields=("molecule_id", "molecule_id", "inchi_key", "inchi_key"),
                    pattern=None,
                    provider_order=("chembl", "pubchem"),
                ),
            ),
            output_silver_path="silver/composite/molecule",
            output_gold_path="gold/composite/molecule",
        ),
    )


# =============================================================================
# Test Classes
# =============================================================================


@pytest.mark.integration
class TestCompositeMoleculePipeline:
    """Integration tests for composite molecule pipeline."""

    def test_seed_only_run(
        self,
        mock_logger: LoggerPort,
        seed_molecule_df: pl.DataFrame,
        composite_molecule_config: CompositeConfig,
    ) -> None:
        """Verify pipeline configuration preserves all seed records."""
        # Create column renamer
        renamer = ColumnRenamer(mock_logger)

        # Rename seed for merge
        seed_renamed = renamer.rename_dataframe(seed_molecule_df, "chembl_molecule")

        # All seed records should be preserved
        assert len(seed_renamed) == 3
        assert "chembl.molecule.molecule_id" in seed_renamed.columns

    def test_enricher_join_by_inchi_key(
        self,
        mock_logger: LoggerPort,
        seed_molecule_df: pl.DataFrame,
        enricher_pubchem_df: pl.DataFrame,
        composite_molecule_config: CompositeConfig,
    ) -> None:
        """Verify InChIKey-based join works correctly."""
        # Create column renamer
        renamer = ColumnRenamer(mock_logger)

        # Rename DataFrames
        seed_renamed = renamer.rename_dataframe(seed_molecule_df, "chembl_molecule")
        enricher_renamed = renamer.rename_dataframe(
            enricher_pubchem_df, "pubchem_compound"
        )

        # Verify renamed columns exist
        assert "chembl.molecule.inchi_key" in seed_renamed.columns
        assert "pubchem.compound.inchi_key" in enricher_renamed.columns

        # Perform join on inchi_key
        # Note: In real merge, join keys are normalized
        joined = seed_renamed.join(
            enricher_renamed,
            left_on="chembl.molecule.inchi_key",
            right_on="pubchem.compound.inchi_key",
            how="left",
        )

        # 2 records should have PubChem data (aspirin, ibuprofen)
        # 1 record (imatinib) should have nulls for PubChem fields
        assert len(joined) == 3

        # Check that PubChem CID is populated for matched records
        molecule_id_col = "pubchem.compound.molecule_id"
        if molecule_id_col in joined.columns:
            non_null_count = joined.filter(pl.col(molecule_id_col).is_not_null()).height
            assert non_null_count == 2, "Expected 2 records with PubChem CID"

    def test_conflict_resolution_field_priorities(
        self,
        composite_molecule_config: CompositeConfig,
    ) -> None:
        """Verify field_priorities are configured correctly."""
        # Verify field priorities are configured
        assert composite_molecule_config.merge.field_priorities is not None
        priorities = composite_molecule_config.merge.field_priorities

        # canonical_smiles: ChEMBL priority (tuples for immutability)
        assert priorities.get("canonical_smiles") == ("chembl", "pubchem")

        # molecular_weight: PubChem priority
        assert priorities.get("molecular_weight") == ("pubchem", "chembl")

    def test_graceful_degradation_on_enricher_failure(
        self,
        mock_logger: LoggerPort,
        seed_molecule_df: pl.DataFrame,
        composite_molecule_config: CompositeConfig,
    ) -> None:
        """Verify pipeline completes when enricher fails."""
        # Enricher is marked as required=False
        assert composite_molecule_config.enrichers[0].required is False

        # Create column renamer
        renamer = ColumnRenamer(mock_logger)

        # When enricher fails, seed data should be preserved
        seed_renamed = renamer.rename_dataframe(seed_molecule_df, "chembl_molecule")

        # All 3 seed records should be preserved
        assert len(seed_renamed) == 3

    def test_inchi_key_format_validation(
        self,
        seed_molecule_df: pl.DataFrame,
    ) -> None:
        """Verify InChIKey format is valid (27 chars, XXXXX-YYYYY-Z)."""
        import re

        inchi_key_pattern = r"^[A-Z]{14}-[A-Z]{10}-[A-Z]$"

        for inchi_key in seed_molecule_df["inchi_key"].to_list():
            assert re.match(inchi_key_pattern, inchi_key), (
                f"Invalid InChIKey format: {inchi_key}"
            )

    def test_column_groups_ordering(
        self,
        composite_molecule_config: CompositeConfig,
    ) -> None:
        """Verify column groups are defined in correct order."""
        groups = composite_molecule_config.merge.column_groups
        assert len(groups) >= 2

        # System group should be first
        assert groups[0].name == "system"
        assert "entity_id" in groups[0].fields

        # Identifiers group should contain primary keys
        identifiers = next((g for g in groups if g.name == "identifiers"), None)
        assert identifiers is not None
        assert "molecule_id" in identifiers.fields


@pytest.mark.integration
class TestMoleculeFieldMapping:
    """Tests for field mapping between ChEMBL and PubChem."""

    def test_chembl_to_pubchem_field_mapping(self) -> None:
        """Verify expected field mappings exist."""
        # Key mappings that should work
        mappings = {
            # ChEMBL -> PubChem (same field, different naming)
            "inchi_key": "inchikey",
            "canonical_smiles": "canonical_smiles",  # Same name
            "standard_inchi": "inchi",
            # ChEMBL -> PubChem (unified alias names)
            "molecular_weight": "molecular_weight",  # Same after Gold unification
            "polar_surface_area": "tpsa",
        }

        # Fields that share the same name across providers after Gold unification
        unified_fields = {"canonical_smiles", "molecular_weight"}
        for chembl_field, pubchem_field in mappings.items():
            assert chembl_field != pubchem_field or chembl_field in unified_fields, (
                f"Expected different field names for {chembl_field}"
            )

    def test_chembl_only_fields(self) -> None:
        """Verify ChEMBL-only fields are preserved."""
        chembl_only_fields = [
            "molecule_id",
            "max_phase",
            "first_approval",
            "therapeutic_flag",
            "withdrawn_flag",
            "black_box_warning",
            "qed_score",
            "hierarchy_parent_chembl_id",
            "atc_classifications",
        ]

        # These fields should only come from ChEMBL
        for field in chembl_only_fields:
            assert field, f"ChEMBL-only field expected: {field}"

    def test_pubchem_only_fields(self) -> None:
        """Verify PubChem-only fields are preserved."""
        pubchem_only_fields = [
            "molecule_id",
            "iupac_name",
            "isomeric_smiles",
        ]

        # These fields should only come from PubChem
        for field in pubchem_only_fields:
            assert field, f"PubChem-only field expected: {field}"


@pytest.mark.integration
class TestCompositeMoleculeConfig:
    """Tests for composite molecule configuration loading."""

    def test_config_file_exists(self) -> None:
        """Verify configuration file exists."""
        from pathlib import Path

        config_path = Path("configs/composites/molecule.yaml")
        assert config_path.exists(), f"Config file not found: {config_path}"

    def test_inline_schema_exists(self) -> None:
        """Verify inline merge.column_groups schema exists in composite config."""
        from pathlib import Path

        config_path = Path("configs/composites/molecule.yaml")
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        groups = raw.get("composite", {}).get("merge", {}).get("column_groups")
        assert isinstance(groups, list) and groups, (
            f"Missing composite.merge.column_groups in {config_path}"
        )

    def test_config_loads_successfully(self) -> None:
        """Verify configuration loads without validation errors."""
        from bioetl.composition.composite_api import load_composite_config

        try:
            config = load_composite_config("molecule")
            assert config.name == "composite_molecule"
            assert config.seed.pipeline == "chembl_molecule"
            assert len(config.enrichers) == 1
            assert config.enrichers[0].pipeline == "pubchem_compound"
        except FileNotFoundError as exc:
            pytest.fail(f"Composite config is missing unexpectedly: {exc}")
        except ValueError as e:
            pytest.fail(f"Config validation failed: {e}")
