"""Performance benchmarks for critical paths.

Run with: pytest tests/benchmarks/ --benchmark-only
Or with comparison: pytest tests/benchmarks/ --benchmark-compare

Requirements:
- pytest-benchmark must be installed
- Benchmarks are skipped if pytest-benchmark is not available
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

# Try to import benchmark fixture, skip tests if not available
try:
    from pytest_benchmark.fixture import BenchmarkFixture

    HAS_BENCHMARK = True
except ImportError:
    HAS_BENCHMARK = False
    BenchmarkFixture = Any  # type: ignore[misc, assignment]


pytestmark = pytest.mark.skipif(
    not HAS_BENCHMARK,
    reason="pytest-benchmark not installed",
)


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
            f"field_{i}": f"value_{i}" if i % 3 != 0 else i * 1.5
            for i in range(80)
        }
        base["nested_list"] = [
            {"id": i, "name": f"item_{i}", "values": list(range(10))}
            for i in range(10)
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
        return {
            f"float_{i}": i * 0.123456789012345
            for i in range(100)
        }

    @pytest.fixture
    def record_with_strings(self) -> dict[str, Any]:
        """Record with strings needing stripping."""
        return {
            f"string_{i}": f"  value with spaces {i}  "
            for i in range(100)
        }

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
            "data": [
                {"nested": {"deep": {"value": i}}}
                for i in range(50)
            ],
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
            "molecule_chembl_id": "CHEMBL123456",
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
            "molecule_chembl_id",
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
