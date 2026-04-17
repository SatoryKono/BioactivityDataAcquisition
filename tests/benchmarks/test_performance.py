"""Performance benchmarks for critical paths.

Run with: pytest tests/benchmarks/ --benchmark-only
Or with comparison: pytest tests/benchmarks/ --benchmark-compare

Requirements:
- pytest-benchmark must be installed
- Benchmarks are skipped if pytest-benchmark is not available

Note: These tests are marked with @pytest.mark.benchmark and excluded from
standard test runs. Run explicitly with: make bench or pytest -m benchmark
"""

from __future__ import annotations

from typing import Any

import pytest

# Try to import benchmark fixture, skip tests if not available
try:
    from pytest_benchmark.fixture import BenchmarkFixture

    HAS_BENCHMARK = True
except ImportError:
    HAS_BENCHMARK = False
    BenchmarkFixture = Any  # type: ignore[misc, assignment]


# Mark all tests in this module as benchmark tests (excluded from standard runs)
pytestmark = [
    pytest.mark.benchmark,
    pytest.mark.skipif(not HAS_BENCHMARK, reason="pytest-benchmark not installed"),
]


# =============================================================================
# Content Hash Benchmarks
# =============================================================================


class TestContentHashPerformance:
    """Benchmarks for content hash generation."""

    @pytest.fixture
    def small_record(self) -> dict[str, Any]:
        """Small record with ~10 fields."""
        return {
            "id": "CHEMBL123456",
            "canonical_smiles": "CCO",
            "pref_name": "Ethanol",
            "molecule_type": "Small molecule",
            "max_phase": 4,
            "therapeutic_flag": True,
            "dosed_ingredient": False,
            "structure_type": "MOL",
            "chirality": 0,
            "prodrug": False,
        }

    @pytest.fixture
    def medium_record(self) -> dict[str, Any]:
        """Medium record with ~50 fields and nested structures."""
        return {
            "id": "CHEMBL123456",
            "canonical_smiles": "CC(C)Cc1ccc(cc1)C(C)C(=O)O",
            "pref_name": "Ibuprofen",
            "molecule_type": "Small molecule",
            "max_phase": 4,
            "therapeutic_flag": True,
            "dosed_ingredient": True,
            "structure_type": "MOL",
            "chirality": 1,
            "prodrug": False,
            "molecule_properties": {
                "alogp": 3.5,
                "aromatic_rings": 1,
                "cx_logd": 0.8,
                "cx_logp": 3.84,
                "cx_most_apka": 4.85,
                "full_mwt": 206.29,
                "hba": 2,
                "hba_lipinski": 2,
                "hbd": 1,
                "hbd_lipinski": 1,
                "heavy_atoms": 15,
                "molecular_species": "ACID",
                "mw_freebase": 206.29,
                "mw_monoisotopic": 206.1307,
                "np_likeness_score": -1.04,
                "num_lipinski_ro5_violations": 0,
                "num_ro5_violations": 0,
                "psa": 37.30,
                "qed_weighted": 0.75,
                "ro3_pass": "N",
                "rtb": 4,
            },
            "molecule_synonyms": [
                {"syn_type": "TRADE_NAME", "molecule_synonym": "Advil"},
                {"syn_type": "TRADE_NAME", "molecule_synonym": "Motrin"},
                {"syn_type": "INN", "molecule_synonym": "Ibuprofen"},
            ],
            "atc_classifications": ["M01AE01", "M02AA13", "G02CC01"],
            "indication_class": "Anti-Inflammatory",
            "usan_stem": "-profen",
            "usan_year": 1968,
            "first_approval": 1969,
            "first_in_class": False,
            "inorganic_flag": False,
            "polymer_flag": False,
            "natural_product": False,
            "oral": True,
            "parenteral": False,
            "topical": True,
            "black_box_warning": False,
            "availability_type": 2,
            "withdrawn_flag": False,
        }

    @pytest.fixture
    def large_record(self) -> dict[str, Any]:
        """Large record with ~100 fields and deep nesting."""
        base = {
            f"field_{i}": f"value_{i}" if i % 3 != 0 else i * 1.5 for i in range(80)
        }
        base["nested_list"] = [
            {"id": i, "name": f"item_{i}", "values": list(range(10))} for i in range(10)
        ]
        base["deep_nested"] = {
            "level1": {
                "level2": {
                    "level3": {
                        "data": list(range(20)),
                        "metadata": {"created": "2024-01-01", "version": 3},
                    }
                }
            }
        }
        return base

    def test_content_hash_small_record(
        self, benchmark: BenchmarkFixture, small_record: dict[str, Any]
    ) -> None:
        """Benchmark content hash for small records (~10 fields)."""
        from bioetl.domain.transformations import generate_content_hash

        result = benchmark(generate_content_hash, small_record, "chembl")
        assert result is not None
        assert len(result) == 64  # SHA256 hex digest

    def test_content_hash_medium_record(
        self, benchmark: BenchmarkFixture, medium_record: dict[str, Any]
    ) -> None:
        """Benchmark content hash for medium records (~50 fields)."""
        from bioetl.domain.transformations import generate_content_hash

        result = benchmark(generate_content_hash, medium_record, "chembl")
        assert result is not None
        assert len(result) == 64

    def test_content_hash_large_record(
        self, benchmark: BenchmarkFixture, large_record: dict[str, Any]
    ) -> None:
        """Benchmark content hash for large records (~100 fields)."""
        from bioetl.domain.transformations import generate_content_hash

        result = benchmark(generate_content_hash, large_record, "chembl")
        assert result is not None
        assert len(result) == 64


# =============================================================================
# Normalization Benchmarks
# =============================================================================


class TestNormalizationPerformance:
    """Benchmarks for data normalization functions."""

    @pytest.fixture
    def record_with_floats(self) -> dict[str, Any]:
        """Record with many float values needing normalization."""
        return {f"float_{i}": i * 0.123456789012345 for i in range(100)}

    @pytest.fixture
    def record_with_strings(self) -> dict[str, Any]:
        """Record with strings needing stripping."""
        return {f"string_{i}": f"  value with spaces {i}  " for i in range(100)}

    def test_normalize_floats(
        self, benchmark: BenchmarkFixture, record_with_floats: dict[str, Any]
    ) -> None:
        """Benchmark float normalization."""
        from bioetl.domain.transformations import normalize_for_hash

        result = benchmark(normalize_for_hash, record_with_floats)
        assert len(result) == 100

    def test_normalize_strings(
        self, benchmark: BenchmarkFixture, record_with_strings: dict[str, Any]
    ) -> None:
        """Benchmark string normalization (strip)."""
        from bioetl.domain.transformations import normalize_for_hash

        result = benchmark(normalize_for_hash, record_with_strings)
        assert len(result) == 100
        # Verify stripping worked
        assert all(not v.startswith(" ") for v in result.values())


# =============================================================================
# JSON Serialization Benchmarks
# =============================================================================


class TestSerializationPerformance:
    """Benchmarks for JSON serialization."""

    @pytest.fixture
    def complex_record(self) -> dict[str, Any]:
        """Complex record for serialization benchmarks."""
        return {
            "id": "test_123",
            "data": [{"nested": {"deep": {"value": i}}} for i in range(50)],
            "metadata": {
                "strings": [f"item_{i}" for i in range(20)],
                "numbers": list(range(100)),
                "booleans": [True, False] * 25,
            },
        }

    def test_canonical_json_dumps(
        self, benchmark: BenchmarkFixture, complex_record: dict[str, Any]
    ) -> None:
        """Benchmark canonical JSON serialization."""
        from bioetl.domain.transformations import canonical_json_dumps

        result = benchmark(canonical_json_dumps, complex_record)
        assert isinstance(result, str)
        assert len(result) > 0


# =============================================================================
# Entity ID Generation Benchmarks
# =============================================================================


class TestEntityIdPerformance:
    """Benchmarks for entity ID generation."""

    @pytest.fixture
    def record_with_id(self) -> dict[str, Any]:
        """Record with explicit ID field."""
        return {
            "molecule_id": "CHEMBL123456",
            "pref_name": "Test Molecule",
            "data": {"key": "value"},
        }

    @pytest.fixture
    def record_without_id(self) -> dict[str, Any]:
        """Record without explicit ID field (fallback to hash)."""
        return {
            "pref_name": "Test Molecule",
            "data": {"key": "value"},
            "properties": {"mw": 250.5, "logp": 2.3},
        }

    def test_entity_id_with_field(
        self, benchmark: BenchmarkFixture, record_with_id: dict[str, Any]
    ) -> None:
        """Benchmark entity ID generation with explicit ID field."""
        from bioetl.domain.transformations import generate_entity_id

        result = benchmark(
            generate_entity_id,
            record_with_id,
            "chembl",
            "molecule_id",
        )
        assert result == "chembl:CHEMBL123456"

    def test_entity_id_hash_fallback(
        self, benchmark: BenchmarkFixture, record_without_id: dict[str, Any]
    ) -> None:
        """Benchmark entity ID generation with hash fallback."""
        from bioetl.domain.transformations import generate_entity_id

        result = benchmark(
            generate_entity_id,
            record_without_id,
            "chembl",
            None,
        )
        assert result.startswith("chembl:")
        assert len(result) == len("chembl:") + 16  # prefix + 16 char hash


# =============================================================================
# Batch Processing Benchmarks
# =============================================================================


class TestBatchProcessingPerformance:
    """Benchmarks for batch processing operations."""

    @pytest.fixture
    def small_batch(self) -> list[dict[str, Any]]:
        """Small batch of 100 records."""
        return [
            {
                "id": f"record_{i}",
                "value": i * 1.5,
                "name": f"Item {i}",
                "active": i % 2 == 0,
            }
            for i in range(100)
        ]

    @pytest.fixture
    def medium_batch(self) -> list[dict[str, Any]]:
        """Medium batch of 1000 records."""
        return [
            {
                "id": f"record_{i}",
                "value": i * 1.5,
                "name": f"Item {i}",
                "active": i % 2 == 0,
                "properties": {"weight": i * 0.1, "volume": i * 0.01},
            }
            for i in range(1000)
        ]

    @pytest.fixture
    def large_batch(self) -> list[dict[str, Any]]:
        """Large batch of 10000 records."""
        return [
            {
                "id": f"record_{i}",
                "value": i * 1.5,
                "name": f"Item {i}",
            }
            for i in range(10000)
        ]

    def test_batch_hash_generation_small(
        self, benchmark: BenchmarkFixture, small_batch: list[dict[str, Any]]
    ) -> None:
        """Benchmark hash generation for small batch."""
        from bioetl.domain.transformations import generate_content_hash

        def hash_batch():
            return [generate_content_hash(r, "test") for r in small_batch]

        result = benchmark(hash_batch)
        assert len(result) == 100

    def test_batch_hash_generation_medium(
        self, benchmark: BenchmarkFixture, medium_batch: list[dict[str, Any]]
    ) -> None:
        """Benchmark hash generation for medium batch."""
        from bioetl.domain.transformations import generate_content_hash

        def hash_batch():
            return [generate_content_hash(r, "test") for r in medium_batch]

        result = benchmark(hash_batch)
        assert len(result) == 1000

    def test_batch_transformation_filter(
        self, benchmark: BenchmarkFixture, medium_batch: list[dict[str, Any]]
    ) -> None:
        """Benchmark filtering records in a batch."""

        def filter_batch():
            return [r for r in medium_batch if r["active"]]

        result = benchmark(filter_batch)
        assert len(result) == 500  # Half are active

    def test_batch_transformation_map(
        self, benchmark: BenchmarkFixture, medium_batch: list[dict[str, Any]]
    ) -> None:
        """Benchmark mapping/transforming records in a batch."""

        def transform_batch():
            return [
                {
                    "entity_id": r["id"],
                    "computed_value": r["value"] * 2,
                    "is_active": r["active"],
                }
                for r in medium_batch
            ]

        result = benchmark(transform_batch)
        assert len(result) == 1000


# =============================================================================
# Polars DataFrame Benchmarks
# =============================================================================


class TestPolarsPerformance:
    """Benchmarks for Polars DataFrame operations."""

    @pytest.fixture
    def records_for_df(self) -> list[dict[str, Any]]:
        """Records for DataFrame creation."""
        return [
            {
                "id": f"record_{i}",
                "value": i * 1.5,
                "name": f"Item {i}",
                "category": f"cat_{i % 10}",
                "active": i % 2 == 0,
            }
            for i in range(5000)
        ]

    def test_polars_from_dicts(
        self, benchmark: BenchmarkFixture, records_for_df: list[dict[str, Any]]
    ) -> None:
        """Benchmark Polars DataFrame creation from dicts."""
        import polars as pl

        result = benchmark(pl.DataFrame, records_for_df)
        assert len(result) == 5000

    def test_polars_filter_operation(
        self, benchmark: BenchmarkFixture, records_for_df: list[dict[str, Any]]
    ) -> None:
        """Benchmark Polars filter operation."""
        import polars as pl

        df = pl.DataFrame(records_for_df)

        def filter_df():
            return df.filter(pl.col("active"))

        result = benchmark(filter_df)
        assert len(result) == 2500

    def test_polars_group_aggregate(
        self, benchmark: BenchmarkFixture, records_for_df: list[dict[str, Any]]
    ) -> None:
        """Benchmark Polars group by and aggregate."""
        import polars as pl

        df = pl.DataFrame(records_for_df)

        def group_agg():
            return df.group_by("category").agg(
                pl.col("value").mean().alias("avg_value"),
                pl.col("active").sum().alias("active_count"),
            )

        result = benchmark(group_agg)
        assert len(result) == 10  # 10 categories


# =============================================================================
# Schema Validation Benchmarks
# =============================================================================


class TestSchemaValidationPerformance:
    """Benchmarks for schema validation operations."""

    @pytest.fixture
    def valid_records(self) -> list[dict[str, Any]]:
        """Records that pass validation."""
        return [
            {
                "entity_id": f"test_{i}",
                "value": float(i),
                "name": f"Name {i}",
                "_run_id": "test-run-id",
                "_run_type": "incremental",
                "_ingestion_ts": "2025-01-15T12:00:00Z",
            }
            for i in range(1000)
        ]

    def test_dict_field_validation(
        self, benchmark: BenchmarkFixture, valid_records: list[dict[str, Any]]
    ) -> None:
        """Benchmark simple field validation."""

        def validate_all():
            results = []
            for record in valid_records:
                is_valid = (
                    "entity_id" in record
                    and "value" in record
                    and isinstance(record["value"], (int, float))
                )
                results.append(is_valid)
            return results

        result = benchmark(validate_all)
        assert all(result)

    def test_comprehensive_validation(
        self, benchmark: BenchmarkFixture, valid_records: list[dict[str, Any]]
    ) -> None:
        """Benchmark comprehensive field validation."""

        required_fields = ["entity_id", "value", "name", "_run_id", "_run_type"]

        def validate_comprehensive():
            results = []
            for record in valid_records:
                is_valid = all(field in record for field in required_fields)
                results.append(is_valid)
            return results

        result = benchmark(validate_comprehensive)
        assert all(result)
