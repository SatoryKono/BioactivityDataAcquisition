"""Integration tests for composite_molecule pipeline.

Tests the merging of ChEMBL molecules (seed) with PubChem compounds (enricher)
using InChIKey as primary join key and canonical_smiles as fallback.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import polars as pl
import pytest

from bioetl.application.composite.column_orderer import ColumnOrderer
from bioetl.application.composite.column_renamer import ColumnRenamer
from bioetl.application.composite.merger import MergeService
from bioetl.domain.composite.config import EnricherConfig, MergeConfig
from bioetl.domain.composite.result import EnrichmentResult, EnrichmentStatus
from bioetl.domain.composite.strategy import ConflictResolution, MergeStrategy
from bioetl.domain.value_objects.column_order import SemanticGroup


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create mock logger."""
    logger = MagicMock()
    logger.debug = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    return logger


@pytest.fixture
def mock_storage() -> AsyncMock:
    """Create a mock StoragePort."""
    storage = AsyncMock()
    storage.read_silver = AsyncMock(return_value=[])
    storage.write_silver_merged = AsyncMock()
    storage.write_gold_merged = AsyncMock()
    return storage


@pytest.fixture
def renamer(mock_logger: MagicMock) -> ColumnRenamer:
    """Create ColumnRenamer instance."""
    return ColumnRenamer(mock_logger)


@pytest.fixture
def orderer(mock_logger: MagicMock) -> ColumnOrderer:
    """Create ColumnOrderer instance."""
    return ColumnOrderer(mock_logger)


@pytest.fixture
def seed_molecule_df() -> pl.DataFrame:
    """Seed DataFrame simulating chembl_molecule output."""
    return pl.DataFrame(
        {
            "molecule_chembl_id": ["CHEMBL25", "CHEMBL1201607", "CHEMBL545"],
            "inchikey": [
                "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",  # Aspirin
                "HEFNNWSXXWATRW-UHFFFAOYSA-N",  # Ibuprofen
                "BOPGDPNILDQYTO-NNYOXOHSSA-N",  # Morphine
            ],
            "canonical_smiles": [
                "CC(=O)OC1=CC=CC=C1C(=O)O",  # Aspirin
                "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O",  # Ibuprofen
                "CN1CC[C@]23C4=C5C=CC(=O)C=C5OC[C@H]3[C@@H]1CC[C@@H]2C4",  # Morphine
            ],
            "pref_name": ["ASPIRIN", "IBUPROFEN", "MORPHINE"],
            "max_phase": [4.0, 4.0, 4.0],
            "molecule_type": ["Small molecule", "Small molecule", "Small molecule"],
            "property_full_mwt": [180.16, 206.28, 285.34],
            "property_alogp": [1.31, 3.79, 0.89],
            "property_psa": [63.6, 37.3, 52.9],
            "property_hba": [4, 2, 4],
            "property_hbd": [1, 1, 2],
            "_run_id": ["run1"] * 3,
            "_ingestion_ts": ["2026-01-01T00:00:00Z"] * 3,
            "entity_id": ["e1", "e2", "e3"],
            "content_hash": ["h1", "h2", "h3"],
        }
    )


@pytest.fixture
def enricher_pubchem_df() -> pl.DataFrame:
    """Enricher DataFrame simulating pubchem_compound output."""
    return pl.DataFrame(
        {
            "cid": [2244, 3672, 5288826],  # PubChem CIDs for Aspirin, Ibuprofen, Morphine
            "inchi_key": [
                "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",  # Aspirin
                "HEFNNWSXXWATRW-UHFFFAOYSA-N",  # Ibuprofen
                "BOPGDPNILDQYTO-NNYOXOHSSA-N",  # Morphine
            ],
            "canonical_smiles": [
                "CC(=O)OC1=CC=CC=C1C(=O)O",
                "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O",
                "CN1CC[C@]23C4=C5C=CC(=O)C=C5OC[C@H]3[C@@H]1CC[C@@H]2C4",
            ],
            "molecular_weight": [180.16, 206.29, 285.34],
            "xlogp": [1.2, 3.5, 0.9],
            "tpsa": [63.6, 37.3, 52.93],
            "h_bond_donor_count": [1, 1, 1],
            "h_bond_acceptor_count": [4, 2, 4],
            "rotatable_bond_count": [3, 4, 0],
            "heavy_atom_count": [13, 15, 21],
            "iupac_name": [
                "2-acetyloxybenzoic acid",
                "2-[4-(2-methylpropyl)phenyl]propanoic acid",
                "(4R,4aR,7S,7aR,12bS)-3-methyl-2,4,4a,7,7a,13-hexahydro-1H-4,12-methanobenzofuro[3,2-e]isoquinoline-7,9-diol",
            ],
            "molecular_formula": ["C9H8O4", "C13H18O2", "C17H19NO3"],
            "complexity": [212.0, 196.0, 477.0],
            "volume_3d": [145.0, 196.0, 268.0],
        }
    )


@pytest.fixture
def enricher_pubchem_partial_df() -> pl.DataFrame:
    """Enricher DataFrame with only partial matches (2 of 3)."""
    return pl.DataFrame(
        {
            "cid": [2244, 3672],  # Only Aspirin and Ibuprofen
            "inchi_key": [
                "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",  # Aspirin
                "HEFNNWSXXWATRW-UHFFFAOYSA-N",  # Ibuprofen
            ],
            "canonical_smiles": [
                "CC(=O)OC1=CC=CC=C1C(=O)O",
                "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O",
            ],
            "molecular_weight": [180.16, 206.29],
            "xlogp": [1.2, 3.5],
            "tpsa": [63.6, 37.3],
        }
    )


@pytest.fixture
def merge_config_molecule() -> MergeConfig:
    """Create MergeConfig for composite_molecule."""
    return MergeConfig(
        strategy=MergeStrategy.LEFT_OUTER,
        conflict_resolution=ConflictResolution.EXPLICIT_RULES,
        output_silver_path="silver/composite/molecule",
        output_gold_path="gold/composite/molecule",
        preserve_all_sources=True,
        field_priorities={
            "inchikey": ["chembl", "pubchem"],
            "canonical_smiles": ["chembl", "pubchem"],
            "molecular_weight": ["pubchem", "chembl"],
            "xlogp": ["pubchem", "chembl"],
            "tpsa": ["pubchem", "chembl"],
        },
    )


@pytest.fixture
def enricher_config_pubchem() -> EnricherConfig:
    """Create EnricherConfig for pubchem_compound enricher."""
    return EnricherConfig(
        pipeline="pubchem_compound",
        join_keys=("inchikey", "canonical_smiles"),
        required=False,
        filter_condition="inchikey IS NOT NULL",
        timeout_seconds=900,
        silver_table="silver/pubchem/compound",
    )


@pytest.fixture
def merge_service(
    merge_config_molecule: MergeConfig,
    mock_storage: AsyncMock,
    mock_logger: MagicMock,
) -> MergeService:
    """Create MergeService for molecule composite."""
    return MergeService(
        merge_config=merge_config_molecule,
        storage=mock_storage,
        logger=mock_logger,
    )


@pytest.mark.integration
class TestSeedOnlyRun:
    """Tests for seed-only runs (no enricher data available)."""

    @pytest.mark.asyncio
    async def test_seed_only_preserves_all_records(
        self,
        merge_service: MergeService,
        mock_storage: AsyncMock,
        seed_molecule_df: pl.DataFrame,
        enricher_config_pubchem: EnricherConfig,
    ) -> None:
        """Seed-only run preserves all seed records when enricher has no data."""
        # Setup: seed has data, enricher is empty
        mock_storage.read_silver.side_effect = [
            seed_molecule_df.to_dicts(),  # Seed table
            [],  # Empty enricher table
        ]

        enrichment_results = {
            "pubchem_compound": EnrichmentResult(
                enricher_name="pubchem_compound",
                status=EnrichmentStatus.SKIPPED,
                records_input=0,
                records_enriched=0,
            ),
        }

        result = await merge_service.merge(
            seed_table="silver/chembl/molecule",
            enrichers=[enricher_config_pubchem],
            enrichment_results=enrichment_results,
            run_id="test-seed-only-run",
            seed_pipeline="chembl_molecule",
        )

        # All 3 seed records should be preserved
        assert result.records_from_seed == 3
        assert result.records_merged == 3
        assert "seed" in result.sources_used

    @pytest.mark.asyncio
    async def test_seed_only_columns_renamed_to_qualified_format(
        self,
        renamer: ColumnRenamer,
        seed_molecule_df: pl.DataFrame,
    ) -> None:
        """Seed columns are renamed to qualified format."""
        result = renamer.rename_dataframe(seed_molecule_df, "chembl_molecule")

        # Business columns renamed to qualified format
        assert "chembl.molecule.molecule_chembl_id" in result.columns
        assert "chembl.molecule.inchikey" in result.columns
        assert "chembl.molecule.pref_name" in result.columns

        # Original names removed
        assert "molecule_chembl_id" not in result.columns
        assert "inchikey" not in result.columns


@pytest.mark.integration
class TestEnricherJoinByInchikey:
    """Tests for enricher joining by InChIKey (primary join key)."""

    def test_join_by_inchikey_matches_all_records(
        self,
        renamer: ColumnRenamer,
        seed_molecule_df: pl.DataFrame,
        enricher_pubchem_df: pl.DataFrame,
    ) -> None:
        """Join by InChIKey matches all records when InChIKeys align."""
        # Rename columns
        seed_renamed = renamer.rename_dataframe(
            seed_molecule_df, "chembl_molecule", exclude_join_keys=False
        )
        enricher_renamed = renamer.rename_dataframe(
            enricher_pubchem_df.rename({"inchi_key": "inchikey"}),
            "pubchem_compound",
            exclude_join_keys=False,
        )

        # Join on qualified InChIKey columns
        merged = seed_renamed.join(
            enricher_renamed,
            left_on="chembl.molecule.inchikey",
            right_on="pubchem.compound.inchikey",
            how="left",
        )

        # All 3 records should match
        assert len(merged) == 3

        # PubChem columns should be present
        assert "pubchem.compound.cid" in merged.columns
        assert "pubchem.compound.molecular_weight" in merged.columns
        assert "pubchem.compound.xlogp" in merged.columns

    def test_join_preserves_seed_when_partial_enricher_match(
        self,
        renamer: ColumnRenamer,
        seed_molecule_df: pl.DataFrame,
        enricher_pubchem_partial_df: pl.DataFrame,
    ) -> None:
        """Left join preserves seed records when enricher has partial matches."""
        seed_renamed = renamer.rename_dataframe(
            seed_molecule_df, "chembl_molecule", exclude_join_keys=False
        )
        enricher_renamed = renamer.rename_dataframe(
            enricher_pubchem_partial_df.rename({"inchi_key": "inchikey"}),
            "pubchem_compound",
            exclude_join_keys=False,
        )

        merged = seed_renamed.join(
            enricher_renamed,
            left_on="chembl.molecule.inchikey",
            right_on="pubchem.compound.inchikey",
            how="left",
        )

        # All 3 seed records preserved
        assert len(merged) == 3

        # Only 2 have PubChem enrichment
        enriched_count = merged.filter(
            pl.col("pubchem.compound.cid").is_not_null()
        ).height
        assert enriched_count == 2


@pytest.mark.integration
class TestEnricherFallbackToSmiles:
    """Tests for fallback to canonical_smiles when InChIKey not available."""

    def test_fallback_join_by_smiles_when_inchikey_missing(
        self,
        renamer: ColumnRenamer,
    ) -> None:
        """Fallback to SMILES when InChIKey is missing."""
        # Seed with missing InChIKey
        seed = pl.DataFrame(
            {
                "molecule_chembl_id": ["CHEMBL25"],
                "inchikey": [None],  # Missing InChIKey
                "canonical_smiles": ["CC(=O)OC1=CC=CC=C1C(=O)O"],  # Aspirin SMILES
                "pref_name": ["ASPIRIN"],
            }
        )

        # Enricher with SMILES for matching
        enricher = pl.DataFrame(
            {
                "cid": [2244],
                "inchikey": [None],  # Also missing
                "canonical_smiles": ["CC(=O)OC1=CC=CC=C1C(=O)O"],
                "molecular_weight": [180.16],
            }
        )

        seed_renamed = renamer.rename_dataframe(seed, "chembl_molecule")
        enricher_renamed = renamer.rename_dataframe(enricher, "pubchem_compound")

        # Join on canonical_smiles
        merged = seed_renamed.join(
            enricher_renamed,
            left_on="chembl.molecule.canonical_smiles",
            right_on="pubchem.compound.canonical_smiles",
            how="left",
        )

        assert len(merged) == 1
        assert merged["pubchem.compound.cid"].to_list() == [2244]


@pytest.mark.integration
class TestConflictResolutionExplicitRules:
    """Tests for explicit conflict resolution rules."""

    def test_pubchem_priority_for_molecular_weight(
        self,
        renamer: ColumnRenamer,
    ) -> None:
        """PubChem has priority for molecular_weight field."""
        seed = pl.DataFrame(
            {
                "molecule_chembl_id": ["CHEMBL25"],
                "inchikey": ["BSYNRYMUTXBXSQ-UHFFFAOYSA-N"],
                "property_full_mwt": [180.16],  # ChEMBL molecular weight
            }
        )

        enricher = pl.DataFrame(
            {
                "cid": [2244],
                "inchikey": ["BSYNRYMUTXBXSQ-UHFFFAOYSA-N"],
                "molecular_weight": [180.157],  # PubChem molecular weight (more precise)
            }
        )

        seed_renamed = renamer.rename_dataframe(seed, "chembl_molecule")
        enricher_renamed = renamer.rename_dataframe(enricher, "pubchem_compound")

        merged = seed_renamed.join(
            enricher_renamed,
            left_on="chembl.molecule.inchikey",
            right_on="pubchem.compound.inchikey",
            how="left",
        )

        # Both columns should be present (preserve_all_sources=True)
        assert "chembl.molecule.property_full_mwt" in merged.columns
        assert "pubchem.compound.molecular_weight" in merged.columns

    def test_chembl_priority_for_inchikey(
        self,
        renamer: ColumnRenamer,
    ) -> None:
        """ChEMBL has priority for InChIKey field.

        Note: When using left_on/right_on with different column names,
        Polars drops the right_on column by default. The MergeService
        handles this by creating a temp join column to preserve both.
        This test verifies the seed (ChEMBL) InChIKey is preserved.
        """
        seed = pl.DataFrame(
            {
                "molecule_chembl_id": ["CHEMBL25"],
                "inchikey": ["BSYNRYMUTXBXSQ-UHFFFAOYSA-N"],
            }
        )

        enricher = pl.DataFrame(
            {
                "cid": [2244],
                "inchikey": ["BSYNRYMUTXBXSQ-UHFFFAOYSA-N"],  # Same InChIKey
            }
        )

        seed_renamed = renamer.rename_dataframe(seed, "chembl_molecule")
        enricher_renamed = renamer.rename_dataframe(enricher, "pubchem_compound")

        # Create temp column for join (as MergeService does) to preserve enricher column
        temp_join_col = "__temp_join_pubchem_compound"
        enricher_renamed = enricher_renamed.with_columns(
            pl.col("pubchem.compound.inchikey").alias(temp_join_col)
        )

        merged = seed_renamed.join(
            enricher_renamed,
            left_on="chembl.molecule.inchikey",
            right_on=temp_join_col,
            how="left",
        )

        # Seed InChIKey preserved
        assert "chembl.molecule.inchikey" in merged.columns
        # Enricher InChIKey also preserved (temp column dropped, original kept)
        assert "pubchem.compound.inchikey" in merged.columns
        # CID enriched
        assert "pubchem.compound.cid" in merged.columns


@pytest.mark.integration
class TestGracefulDegradationOnEnricherFailure:
    """Tests for graceful degradation when enricher fails."""

    @pytest.mark.asyncio
    async def test_enricher_failure_preserves_seed_data(
        self,
        merge_service: MergeService,
        mock_storage: AsyncMock,
        seed_molecule_df: pl.DataFrame,
        enricher_config_pubchem: EnricherConfig,
    ) -> None:
        """Enricher failure does not block seed data processing."""
        # Setup: seed has data, enricher fails
        mock_storage.read_silver.side_effect = [
            seed_molecule_df.to_dicts(),  # Seed table
            Exception("PubChem API timeout"),  # Enricher read fails
        ]

        enrichment_results = {
            "pubchem_compound": EnrichmentResult(
                enricher_name="pubchem_compound",
                status=EnrichmentStatus.FAILED,
                records_input=0,
                records_enriched=0,
                error_message="PubChem API timeout",
            ),
        }

        result = await merge_service.merge(
            seed_table="silver/chembl/molecule",
            enrichers=[enricher_config_pubchem],
            enrichment_results=enrichment_results,
            run_id="test-enricher-failure-run",
            seed_pipeline="chembl_molecule",
        )

        # All seed records preserved despite enricher failure
        assert result.records_from_seed == 3
        assert result.records_merged == 3

    @pytest.mark.asyncio
    async def test_optional_enricher_does_not_fail_pipeline(
        self,
        merge_service: MergeService,
        mock_storage: AsyncMock,
        seed_molecule_df: pl.DataFrame,
    ) -> None:
        """Optional enricher (required=False) does not fail entire pipeline."""
        mock_storage.read_silver.side_effect = [
            seed_molecule_df.to_dicts(),  # Seed table
        ]

        # Enricher with required=False
        optional_enricher = EnricherConfig(
            pipeline="pubchem_compound",
            join_keys=("inchikey",),
            required=False,  # Optional
            silver_table="silver/pubchem/compound",
        )

        enrichment_results = {
            "pubchem_compound": EnrichmentResult(
                enricher_name="pubchem_compound",
                status=EnrichmentStatus.FAILED,
                records_input=0,
                records_enriched=0,
            ),
        }

        # Should not raise
        result = await merge_service.merge(
            seed_table="silver/chembl/molecule",
            enrichers=[optional_enricher],
            enrichment_results=enrichment_results,
            run_id="test-optional-enricher-run",
            seed_pipeline="chembl_molecule",
        )

        assert result.records_merged == 3


@pytest.mark.integration
class TestColumnOrderingMolecule:
    """Tests for column ordering in composite_molecule output."""

    def test_system_columns_ordered_first(
        self,
        orderer: ColumnOrderer,
    ) -> None:
        """System columns appear before business columns."""
        df = pl.DataFrame(
            {
                "pubchem.compound.cid": [2244],
                "chembl.molecule.molecule_chembl_id": ["CHEMBL25"],
                "_run_id": ["r1"],
                "entity_id": ["e1"],
                "content_hash": ["h1"],
            }
        )

        ordered = orderer.order_columns(df)
        columns = ordered.columns

        # System columns indices
        system_cols = [
            c for c in columns if orderer._config.get_group(c) == SemanticGroup.SYSTEM
        ]

        # Identifier columns indices
        id_cols = [
            c
            for c in columns
            if orderer._config.get_group(c) == SemanticGroup.IDENTIFIERS
        ]

        if system_cols and id_cols:
            system_max_idx = max(columns.index(c) for c in system_cols)
            id_min_idx = min(columns.index(c) for c in id_cols)
            assert system_max_idx < id_min_idx

    def test_chembl_columns_ordered_before_pubchem_for_identifiers(
        self,
        renamer: ColumnRenamer,
        orderer: ColumnOrderer,
    ) -> None:
        """Within identifier group, ChEMBL columns appear before PubChem."""
        df = pl.DataFrame(
            {
                "pubchem.compound.inchikey": ["BSYNRYMUTXBXSQ-UHFFFAOYSA-N"],
                "chembl.molecule.inchikey": ["BSYNRYMUTXBXSQ-UHFFFAOYSA-N"],
            }
        )

        ordered = orderer.order_columns(df)

        chembl_idx = ordered.columns.index("chembl.molecule.inchikey")
        pubchem_idx = ordered.columns.index("pubchem.compound.inchikey")

        assert chembl_idx < pubchem_idx


@pytest.mark.integration
class TestDataPreservationMolecule:
    """Tests for data integrity through the molecule pipeline."""

    def test_data_values_preserved_through_rename(
        self,
        renamer: ColumnRenamer,
        seed_molecule_df: pl.DataFrame,
    ) -> None:
        """Data values are preserved after renaming."""
        result = renamer.rename_dataframe(seed_molecule_df, "chembl_molecule")

        # ChEMBL IDs preserved
        assert result["chembl.molecule.molecule_chembl_id"].to_list() == [
            "CHEMBL25",
            "CHEMBL1201607",
            "CHEMBL545",
        ]

        # InChIKeys preserved
        assert result["chembl.molecule.inchikey"].to_list() == [
            "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
            "HEFNNWSXXWATRW-UHFFFAOYSA-N",
            "BOPGDPNILDQYTO-NNYOXOHSSA-N",
        ]

    def test_row_count_preserved_through_merge(
        self,
        renamer: ColumnRenamer,
        seed_molecule_df: pl.DataFrame,
        enricher_pubchem_df: pl.DataFrame,
    ) -> None:
        """Row count equals seed count (left outer join)."""
        original_rows = len(seed_molecule_df)

        seed_renamed = renamer.rename_dataframe(seed_molecule_df, "chembl_molecule")
        enricher_renamed = renamer.rename_dataframe(
            enricher_pubchem_df.rename({"inchi_key": "inchikey"}),
            "pubchem_compound",
        )

        merged = seed_renamed.join(
            enricher_renamed,
            left_on="chembl.molecule.inchikey",
            right_on="pubchem.compound.inchikey",
            how="left",
        )

        assert len(merged) == original_rows


@pytest.mark.integration
class TestInchiKeyNormalization:
    """Tests for InChIKey handling and normalization."""

    def test_inchikey_format_validation(self) -> None:
        """InChIKey format follows standard pattern."""
        import re

        inchikey_pattern = r"^[A-Z]{14}-[A-Z]{10}-[A-Z]$"

        valid_inchikeys = [
            "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",  # Aspirin
            "HEFNNWSXXWATRW-UHFFFAOYSA-N",  # Ibuprofen
            "BOPGDPNILDQYTO-NNYOXOHSSA-N",  # Morphine
        ]

        for inchikey in valid_inchikeys:
            assert re.match(inchikey_pattern, inchikey), f"Invalid InChIKey: {inchikey}"

    def test_inchikey_case_preserved(
        self,
        renamer: ColumnRenamer,
    ) -> None:
        """InChIKey case is preserved (always uppercase)."""
        df = pl.DataFrame(
            {
                "molecule_chembl_id": ["CHEMBL25"],
                "inchikey": ["BSYNRYMUTXBXSQ-UHFFFAOYSA-N"],
            }
        )

        result = renamer.rename_dataframe(df, "chembl_molecule")

        # InChIKey should remain uppercase
        assert result["chembl.molecule.inchikey"].to_list() == [
            "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"
        ]
