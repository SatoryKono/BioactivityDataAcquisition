"""Unit tests for Gold strict validation paths.

Tests GoldWriterValidationMixin strict schema validation and mode validation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandera.pandas as pandera_pa
import pytest

from bioetl.domain.medallion import GoldWriteMode
from bioetl.domain.types import ScdConfig

FIXED_INGESTION_TS = datetime(2024, 1, 1, 12, 0, 0)


@pytest.mark.unit
class TestGoldStrictValidationPaths:
    """Unit tests for Gold strict validation paths.

    Tests strict schema validation, mode validation, and SCD2 requirements.
    """

    def test_validate_write_mode_valid_modes(self) -> None:
        """Test validation of valid Gold write modes."""
        from bioetl.infrastructure.storage.gold.validation_mixin import (
            GoldWriterValidationMixin,
        )

        class TestWriter(GoldWriterValidationMixin):
            pass

        writer = TestWriter()

        # Test all valid modes
        for mode_str in ["append", "overwrite", "scd2"]:
            mode = writer._validate_write_mode(mode_str)
            assert isinstance(mode, GoldWriteMode)

    def test_validate_write_mode_invalid_mode(self) -> None:
        """Test validation rejects invalid Gold write modes."""
        from bioetl.infrastructure.storage.gold.validation_mixin import (
            GoldWriterValidationMixin,
        )

        class TestWriter(GoldWriterValidationMixin):
            pass

        writer = TestWriter()

        # Test invalid mode
        with pytest.raises(ValueError, match="Invalid Gold write mode"):
            writer._validate_write_mode("invalid_mode")

    def test_validate_records_empty_raises_strict_mode(self) -> None:
        """Test validation rejects empty records list."""
        from bioetl.infrastructure.storage.gold.validation_mixin import (
            GoldWriterValidationMixin,
        )

        class TestWriter(GoldWriterValidationMixin):
            pass

        writer = TestWriter()

        # Test empty records
        with pytest.raises(ValueError, match="No records to write"):
            writer._validate_records([])

    def test_validate_records_with_records(self) -> None:
        """Test validation accepts non-empty records list."""
        from bioetl.infrastructure.storage.gold.validation_mixin import (
            GoldWriterValidationMixin,
        )

        class TestWriter(GoldWriterValidationMixin):
            pass

        writer = TestWriter()

        # Test non-empty records (should not raise)
        writer._validate_records([{"id": 1}, {"id": 2}])

    def test_validate_scd2_requirements_valid(self) -> None:
        """Test SCD2 validation accepts valid configuration."""
        from bioetl.infrastructure.storage.gold.validation_mixin import (
            GoldWriterValidationMixin,
        )

        class TestWriter(GoldWriterValidationMixin):
            pass

        writer = TestWriter()

        scd_config = ScdConfig(
            scd_type=2,
            business_key="id",
            valid_from_col="valid_from",
            valid_to_col="valid_to",
        )

        # Test valid SCD2 configuration (should not raise)
        writer._validate_scd2_requirements(
            mode=GoldWriteMode.SCD2,
            scd_config=scd_config,
            ingestion_ts=FIXED_INGESTION_TS,
        )

    def test_validate_scd2_requires_config(self) -> None:
        """Test SCD2 validation requires scd_config."""
        from bioetl.infrastructure.storage.gold.validation_mixin import (
            GoldWriterValidationMixin,
        )

        class TestWriter(GoldWriterValidationMixin):
            pass

        writer = TestWriter()

        # Test missing scd_config
        with pytest.raises(ValueError, match="scd_config required"):
            writer._validate_scd2_requirements(
                mode=GoldWriteMode.SCD2,
                scd_config=None,
                ingestion_ts=FIXED_INGESTION_TS,
            )

    def test_validate_scd2_requires_type_2(self) -> None:
        """Test SCD2 validation requires scd_type=2."""
        from bioetl.infrastructure.storage.gold.validation_mixin import (
            GoldWriterValidationMixin,
        )

        class TestWriter(GoldWriterValidationMixin):
            pass

        writer = TestWriter()

        scd_config = ScdConfig(
            scd_type=1,  # Wrong type
            business_key="id",
            valid_from_col="valid_from",
            valid_to_col="valid_to",
        )

        # Test wrong scd_type
        with pytest.raises(ValueError, match="scd_config.type must be 2"):
            writer._validate_scd2_requirements(
                mode=GoldWriteMode.SCD2,
                scd_config=scd_config,
                ingestion_ts=FIXED_INGESTION_TS,
            )

    def test_validate_scd2_requires_business_keys(self) -> None:
        """Test SCD2 validation requires business_keys."""
        from bioetl.infrastructure.storage.gold.validation_mixin import (
            GoldWriterValidationMixin,
        )

        class TestWriter(GoldWriterValidationMixin):
            pass

        writer = TestWriter()

        scd_config = ScdConfig(
            scd_type=2,
            business_key=None,
            valid_from_col="valid_from",
            valid_to_col="valid_to",
        )

        # Test empty business_keys
        with pytest.raises(ValueError, match="scd_config.business_key required"):
            writer._validate_scd2_requirements(
                mode=GoldWriteMode.SCD2,
                scd_config=scd_config,
                ingestion_ts=FIXED_INGESTION_TS,
            )

    def test_validate_scd2_requires_ingestion_ts(self) -> None:
        """Test SCD2 validation requires ingestion_ts."""
        from bioetl.infrastructure.storage.gold.validation_mixin import (
            GoldWriterValidationMixin,
        )

        class TestWriter(GoldWriterValidationMixin):
            pass

        writer = TestWriter()

        scd_config = ScdConfig(
            scd_type=2,
            business_key="id",
            valid_from_col="valid_from",
            valid_to_col="valid_to",
        )

        # Test missing ingestion_ts
        with pytest.raises(ValueError, match="ingestion_ts required"):
            writer._validate_scd2_requirements(
                mode=GoldWriteMode.SCD2,
                scd_config=scd_config,
                ingestion_ts=None,
            )

    def test_validate_scd2_skips_for_non_scd2_modes(self) -> None:
        """Test SCD2 validation is skipped for non-SCD2 modes."""
        from bioetl.infrastructure.storage.gold.validation_mixin import (
            GoldWriterValidationMixin,
        )

        class TestWriter(GoldWriterValidationMixin):
            pass

        writer = TestWriter()

        # Test append mode (should not raise)
        writer._validate_scd2_requirements(
            mode=GoldWriteMode.APPEND,
            scd_config=None,
            ingestion_ts=None,
        )

        # Test overwrite mode (should not raise)
        writer._validate_scd2_requirements(
            mode=GoldWriteMode.OVERWRITE,
            scd_config=None,
            ingestion_ts=None,
        )

    def test_validate_schema_strict_true(self) -> None:
        """Test schema validation accepts strict=True schemas."""
        from bioetl.infrastructure.storage.gold.validation_mixin import (
            GoldWriterValidationMixin,
        )

        class TestWriter(GoldWriterValidationMixin):
            pass

        writer = TestWriter()

        # Create strict schema
        schema = pandera_pa.DataFrameSchema(
            columns={"id": pandera_pa.Column(int)},
            strict=True,
        )

        # Test strict schema (should not raise)
        writer._validate_schema_strict(schema)

    def test_validate_schema_strict_false(self) -> None:
        """Test schema validation rejects non-strict schemas."""
        from bioetl.infrastructure.storage.gold.validation_mixin import (
            GoldWriterValidationMixin,
        )

        class TestWriter(GoldWriterValidationMixin):
            pass

        writer = TestWriter()

        # Create non-strict schema
        schema = pandera_pa.DataFrameSchema(
            columns={"id": pandera_pa.Column(int)},
            strict=False,
        )

        # Test non-strict schema (should raise)
        with pytest.raises(
            ValueError,
            match="Gold layer requires strict=True schema validation",
        ):
            writer._validate_schema_strict(schema)

    def test_validate_schema_strict_default(self) -> None:
        """Test schema validation rejects schemas without strict setting."""
        from bioetl.infrastructure.storage.gold.validation_mixin import (
            GoldWriterValidationMixin,
        )

        class TestWriter(GoldWriterValidationMixin):
            pass

        writer = TestWriter()

        # Create schema without strict setting
        schema = pandera_pa.DataFrameSchema(
            columns={"id": pandera_pa.Column(int)},
        )

        # Test default schema (should raise)
        with pytest.raises(
            ValueError,
            match="Gold layer requires strict=True schema validation",
        ):
            writer._validate_schema_strict(schema)


@pytest.mark.unit
class TestGoldValidationIntegration:
    """Integration tests for Gold validation path combinations."""

    def test_full_validation_chain_valid(self) -> None:
        """Test complete validation chain with valid inputs."""
        from bioetl.infrastructure.storage.gold.validation_mixin import (
            GoldWriterValidationMixin,
        )

        class TestWriter(GoldWriterValidationMixin):
            pass

        writer = TestWriter()

        # Validate mode
        mode = writer._validate_write_mode("append")

        # Validate records
        writer._validate_records([{"id": 1}])

        # Validate schema
        schema = pandera_pa.DataFrameSchema(
            columns={"id": pandera_pa.Column(int)},
            strict=True,
        )
        writer._validate_schema_strict(schema)

        # All validations should pass
        assert mode == GoldWriteMode.APPEND

    def test_full_validation_chain_invalid_mode(self) -> None:
        """Test validation chain fails on invalid mode."""
        from bioetl.infrastructure.storage.gold.validation_mixin import (
            GoldWriterValidationMixin,
        )

        class TestWriter(GoldWriterValidationMixin):
            pass

        writer = TestWriter()

        # Should fail on mode validation
        with pytest.raises(ValueError, match="Invalid Gold write mode"):
            writer._validate_write_mode("invalid")

    def test_scd2_full_validation_chain(self) -> None:
        """Test complete SCD2 validation chain."""
        from bioetl.infrastructure.storage.gold.validation_mixin import (
            GoldWriterValidationMixin,
        )

        class TestWriter(GoldWriterValidationMixin):
            pass

        writer = TestWriter()

        # Validate mode
        mode = writer._validate_write_mode("scd2")

        # Validate records
        writer._validate_records([{"id": 1}])

        # Validate SCD2 requirements
        scd_config = ScdConfig(
            scd_type=2,
            business_key="id",
            valid_from_col="valid_from",
            valid_to_col="valid_to",
        )
        writer._validate_scd2_requirements(
            mode=mode,
            scd_config=scd_config,
            ingestion_ts=FIXED_INGESTION_TS,
        )

        # Validate schema
        schema = pandera_pa.DataFrameSchema(
            columns={"id": pandera_pa.Column(int)},
            strict=True,
        )
        writer._validate_schema_strict(schema)

        # All validations should pass
        assert mode == GoldWriteMode.SCD2
