"""Golden tests for output determinism.

These tests verify that the deterministic writer produces
byte-for-byte identical outputs for the same input data,
even when the input order varies.
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from bioetl.domain.output.deterministic import DeterministicWriterABC
from bioetl.infrastructure.adapters.pandas_tabular import PandasTabularAdapter
from bioetl.infrastructure.output.deterministic import (
    DeterministicCSVWriter,
    DeterministicParquetWriter,
)


@pytest.fixture
def sample_data() -> pd.DataFrame:
    """Create sample test data."""
    return pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "name": ["Alice", "Bob", "Charlie", "Diana", "Eve"],
        "value": [100.0, 200.5, 300.25, 400.125, 500.0625],
    })


@pytest.fixture
def shuffled_data(sample_data: pd.DataFrame) -> pd.DataFrame:
    """Create shuffled version of sample data."""
    shuffled = sample_data.sample(frac=1, random_state=42).reset_index(drop=True)
    return shuffled


@pytest.fixture
def parquet_writer() -> DeterministicWriterABC:
    """Create Parquet writer instance."""
    return DeterministicParquetWriter()


@pytest.fixture
def csv_writer() -> DeterministicWriterABC:
    """Create CSV writer instance."""
    return DeterministicCSVWriter()


class TestDeterministicParquetWriter:
    """Tests for DeterministicParquetWriter."""

    def test_identical_input_produces_identical_output(
        self,
        parquet_writer: DeterministicWriterABC,
        sample_data: pd.DataFrame,
        tmp_path: Path,
    ) -> None:
        """Same input should produce byte-identical output."""
        path1 = tmp_path / "output1.parquet"
        path2 = tmp_path / "output2.parquet"

        tabular = PandasTabularAdapter(sample_data)

        result1 = parquet_writer.write_atomic(tabular, path1)
        result2 = parquet_writer.write_atomic(tabular, path2)

        assert result1.checksum == result2.checksum
        assert path1.read_bytes() == path2.read_bytes()

    def test_shuffled_input_produces_same_sorted_output(
        self,
        parquet_writer: DeterministicWriterABC,
        sample_data: pd.DataFrame,
        shuffled_data: pd.DataFrame,
        tmp_path: Path,
    ) -> None:
        """Shuffled input with same content should produce identical sorted output."""
        path1 = tmp_path / "sorted1.parquet"
        path2 = tmp_path / "sorted2.parquet"

        tabular1 = PandasTabularAdapter(sample_data)
        tabular2 = PandasTabularAdapter(shuffled_data)

        result1 = parquet_writer.write_atomic(
            tabular1, path1, sort_columns=("id",)
        )
        result2 = parquet_writer.write_atomic(
            tabular2, path2, sort_columns=("id",)
        )

        assert result1.checksum == result2.checksum
        assert path1.read_bytes() == path2.read_bytes()

    def test_atomic_write_creates_file(
        self,
        parquet_writer: DeterministicWriterABC,
        sample_data: pd.DataFrame,
        tmp_path: Path,
    ) -> None:
        """Atomic write should create the target file."""
        path = tmp_path / "output.parquet"
        tabular = PandasTabularAdapter(sample_data)

        result = parquet_writer.write_atomic(tabular, path)

        assert path.exists()
        assert result.path == path
        assert result.row_count == len(sample_data)
        assert result.is_atomic

    def test_checksum_verification(
        self,
        parquet_writer: DeterministicWriterABC,
        sample_data: pd.DataFrame,
        tmp_path: Path,
    ) -> None:
        """Checksum verification should work correctly."""
        path = tmp_path / "output.parquet"
        tabular = PandasTabularAdapter(sample_data)

        result = parquet_writer.write_atomic(tabular, path)

        assert parquet_writer.verify_checksum(path, result.checksum)
        assert not parquet_writer.verify_checksum(path, "invalid_checksum")

    def test_multiple_random_shuffles_produce_same_output(
        self,
        parquet_writer: DeterministicWriterABC,
        sample_data: pd.DataFrame,
        tmp_path: Path,
    ) -> None:
        """Multiple random shuffles should all produce identical sorted output."""
        reference_path = tmp_path / "reference.parquet"
        tabular_ref = PandasTabularAdapter(sample_data)
        ref_result = parquet_writer.write_atomic(
            tabular_ref, reference_path, sort_columns=("id",)
        )

        for i in range(5):
            shuffled = sample_data.sample(frac=1, random_state=i * 42)
            path = tmp_path / f"shuffled_{i}.parquet"
            tabular = PandasTabularAdapter(shuffled)

            result = parquet_writer.write_atomic(
                tabular, path, sort_columns=("id",)
            )

            assert result.checksum == ref_result.checksum, (
                f"Shuffle {i} produced different checksum"
            )


class TestDeterministicCSVWriter:
    """Tests for DeterministicCSVWriter."""

    def test_identical_input_produces_identical_output(
        self,
        csv_writer: DeterministicWriterABC,
        sample_data: pd.DataFrame,
        tmp_path: Path,
    ) -> None:
        """Same input should produce byte-identical output."""
        path1 = tmp_path / "output1.csv"
        path2 = tmp_path / "output2.csv"

        tabular = PandasTabularAdapter(sample_data)

        result1 = csv_writer.write_atomic(tabular, path1)
        result2 = csv_writer.write_atomic(tabular, path2)

        assert result1.checksum == result2.checksum
        assert path1.read_bytes() == path2.read_bytes()

    def test_shuffled_input_produces_same_sorted_output(
        self,
        csv_writer: DeterministicWriterABC,
        sample_data: pd.DataFrame,
        shuffled_data: pd.DataFrame,
        tmp_path: Path,
    ) -> None:
        """Shuffled input with same content should produce identical sorted output."""
        path1 = tmp_path / "sorted1.csv"
        path2 = tmp_path / "sorted2.csv"

        tabular1 = PandasTabularAdapter(sample_data)
        tabular2 = PandasTabularAdapter(shuffled_data)

        result1 = csv_writer.write_atomic(
            tabular1, path1, sort_columns=("id",)
        )
        result2 = csv_writer.write_atomic(
            tabular2, path2, sort_columns=("id",)
        )

        assert result1.checksum == result2.checksum


class TestWriteResultVerification:
    """Tests for WriteResult verification."""

    def test_verify_returns_true_for_matching_checksum(
        self,
        parquet_writer: DeterministicWriterABC,
        sample_data: pd.DataFrame,
        tmp_path: Path,
    ) -> None:
        """WriteResult.verify should return True for matching checksum."""
        path = tmp_path / "output.parquet"
        tabular = PandasTabularAdapter(sample_data)

        result = parquet_writer.write_atomic(tabular, path)

        assert result.verify(result.checksum)

    def test_verify_returns_false_for_mismatched_checksum(
        self,
        parquet_writer: DeterministicWriterABC,
        sample_data: pd.DataFrame,
        tmp_path: Path,
    ) -> None:
        """WriteResult.verify should return False for mismatched checksum."""
        path = tmp_path / "output.parquet"
        tabular = PandasTabularAdapter(sample_data)

        result = parquet_writer.write_atomic(tabular, path)

        assert not result.verify("wrong_checksum_value")
