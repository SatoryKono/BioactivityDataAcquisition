# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Pytest fixtures for performance benchmarks.

These fixtures provide consistent test data for reproducible benchmarks.
All data is synthetic and deterministic to ensure stable measurements.
"""

import json
from pathlib import Path
from typing import Any

import pytest

try:
    from pytest_benchmark.fixture import BenchmarkFixture

    HAS_BENCHMARK = True
except ImportError:
    HAS_BENCHMARK = False
    BenchmarkFixture = Any  # type: ignore[misc, assignment]


def _benchmark_plugin_active(config: pytest.Config) -> bool:
    """Return whether the pytest-benchmark plugin is active for this run."""
    pluginmanager = config.pluginmanager
    return any(
        pluginmanager.hasplugin(name)
        for name in ("benchmark", "pytest_benchmark", "pytest-benchmark")
    )


class _DisabledBenchmarkFixturePlugin:
    """Provide a skip-only benchmark fixture when the plugin is disabled."""

    @pytest.fixture
    def benchmark(self) -> BenchmarkFixture:
        pytest.skip("pytest-benchmark plugin is not active; run with '-p benchmark'")


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    """Register a fallback benchmark fixture when the plugin is unavailable."""
    if _benchmark_plugin_active(config):
        return

    plugin_name = "bioetl-disabled-benchmark-fixture"
    if config.pluginmanager.hasplugin(plugin_name):
        return

    config.pluginmanager.register(_DisabledBenchmarkFixturePlugin(), plugin_name)


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item: pytest.Item) -> None:
    """Skip benchmark-marked tests before fixture resolution when plugin is off."""
    if "benchmark" not in item.keywords:
        return
    if _benchmark_plugin_active(item.config):
        return
    pytest.skip("pytest-benchmark plugin is not active; run with '-p benchmark'")


@pytest.fixture
def small_payload() -> list[dict[str, Any]]:
    """Small payload for quick benchmarks (100 records)."""
    return [
        {
            "id": f"RECORD_{i:05d}",
            "molecule_id": f"CHEMBL{100000 + i}",
            "assay_id": f"CHEMBL{200000 + i}",
            "target_id": f"CHEMBL{300000 + i}",
            "standard_value": 10.5 + (i * 0.1),
            "standard_units": "nM",
            "pchembl_value": 7.5 + (i * 0.01),
            "data_validity_comment": None,
            "canonical_smiles": f"CC{'C' * (i % 10)}O",
        }
        for i in range(100)
    ]


@pytest.fixture
def medium_payload() -> list[dict[str, Any]]:
    """Medium payload for standard benchmarks (1000 records)."""
    return [
        {
            "id": f"RECORD_{i:06d}",
            "molecule_id": f"CHEMBL{100000 + i}",
            "assay_id": f"CHEMBL{200000 + i}",
            "target_id": f"CHEMBL{300000 + i}",
            "publication_id": f"CHEMBL{400000 + i}",
            "standard_value": 10.5 + (i * 0.1),
            "standard_units": "nM",
            "pchembl_value": 7.5 + (i * 0.01),
            "standard_type": "IC50",
            "activity_comment": f"Activity measured at concentration {i}",
            "data_validity_comment": None,
            "canonical_smiles": f"CC{'C' * (i % 20)}O",
            "molecule_properties": {
                "mw_freebase": 200.0 + i,
                "alogp": 2.5 + (i * 0.01),
                "hba": 2 + (i % 5),
                "hbd": 1 + (i % 3),
                "psa": 40.0 + (i * 0.5),
                "rtb": 3 + (i % 4),
            },
        }
        for i in range(1000)
    ]


@pytest.fixture
def large_payload() -> list[dict[str, Any]]:
    """Large payload for stress benchmarks (5000 records)."""
    return [
        {
            "id": f"RECORD_{i:07d}",
            "molecule_id": f"CHEMBL{100000 + i}",
            "assay_id": f"CHEMBL{200000 + i}",
            "target_id": f"CHEMBL{300000 + i}",
            "publication_id": f"CHEMBL{400000 + i}",
            "standard_value": 10.5 + (i * 0.1),
            "standard_units": "nM",
            "pchembl_value": 7.5 + (i * 0.01),
            "standard_type": "IC50",
            "activity_comment": f"Activity measured at concentration {i}" * 3,
            "data_validity_comment": None,
            "canonical_smiles": f"CC{'C' * (i % 30)}O" * 2,
            "molecule_properties": {
                "mw_freebase": 200.0 + i,
                "alogp": 2.5 + (i * 0.01),
                "hba": 2 + (i % 5),
                "hbd": 1 + (i % 3),
                "psa": 40.0 + (i * 0.5),
                "rtb": 3 + (i % 4),
                "num_ro5_violations": i % 2,
                "aromatic_rings": 1 + (i % 3),
            },
            "assay_description": f"High-throughput assay variant {i % 100}",
            "bao_format": "BAO_0000357",
            "src_id": 1,
        }
        for i in range(5000)
    ]


@pytest.fixture
def bronze_output_dir(tmp_path: Path) -> Path:
    """Temporary directory for bronze output."""
    bronze_dir = tmp_path / "bronze"
    bronze_dir.mkdir(parents=True, exist_ok=True)
    return bronze_dir


@pytest.fixture
def delta_output_dir(tmp_path: Path) -> Path:
    """Temporary directory for delta table output."""
    delta_dir = tmp_path / "delta"
    delta_dir.mkdir(parents=True, exist_ok=True)
    return delta_dir


if not HAS_BENCHMARK:

    @pytest.fixture
    def benchmark() -> BenchmarkFixture:
        """Skip benchmark tests cleanly when pytest-benchmark is unavailable."""
        pytest.skip("pytest-benchmark not installed")


def calculate_payload_size_mb(payload: list[dict]) -> float:
    """Calculate approximate payload size in MB."""
    json_str = json.dumps(payload)
    return len(json_str.encode("utf-8")) / (1024 * 1024)
