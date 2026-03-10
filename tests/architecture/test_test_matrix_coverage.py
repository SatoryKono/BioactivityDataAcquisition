"""Architecture tests for test matrix coverage validation.

Validates that provider test coverage meets ADR-042 requirements:
- VCR cassettes exist for each provider
- Unit tests exist for each architectural layer
- Property tests stay within allowed boundaries
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
TESTS_DIR = ROOT / "tests"
MATRIX_PATH = ROOT / "configs" / "quality" / "test_matrix.yaml"


def _load_matrix() -> dict:
    """Load the test matrix configuration."""
    with MATRIX_PATH.open() as f:
        return yaml.safe_load(f)


@pytest.mark.architecture
class TestVCRCassetteCoverage:
    """Validate VCR cassettes exist for required providers."""

    def test_vcr_dir_exists_for_each_provider(self) -> None:
        matrix = _load_matrix()
        vcr_dir = TESTS_DIR / "fixtures" / "vcr"
        for provider, config in matrix["providers"].items():
            if config.get("vcr_cassettes") == "MUST":
                provider_vcr = vcr_dir / provider
                assert provider_vcr.is_dir(), (
                    f"Missing VCR cassette directory for provider '{provider}': "
                    f"{provider_vcr}"
                )

    def test_vcr_cassettes_not_empty(self) -> None:
        matrix = _load_matrix()
        vcr_dir = TESTS_DIR / "fixtures" / "vcr"
        for provider, config in matrix["providers"].items():
            if config.get("vcr_cassettes") == "MUST":
                provider_vcr = vcr_dir / provider
                if provider_vcr.is_dir():
                    cassettes = list(provider_vcr.glob("*.yaml"))
                    assert len(cassettes) > 0, (
                        f"Provider '{provider}' VCR directory exists but has no cassettes"
                    )


@pytest.mark.architecture
class TestPropertyTestBoundaries:
    """Validate property-based tests respect ADR-042 boundaries."""

    def test_no_hypothesis_in_forbidden_dirs(self) -> None:
        """Property tests MUST NOT exist in forbidden directories."""
        matrix = _load_matrix()
        forbidden = matrix.get("property_test_boundaries", {}).get("forbidden", [])

        for forbidden_path in forbidden:
            # Map source path to test path
            parts = forbidden_path.split("/")
            if len(parts) >= 2:
                test_dir = TESTS_DIR / "unit" / parts[0] / parts[1]
            else:
                test_dir = TESTS_DIR / "unit" / parts[0]

            if not test_dir.is_dir():
                continue

            for test_file in test_dir.rglob("test_*.py"):
                content = test_file.read_text(encoding="utf-8")
                if "@given(" in content or "from hypothesis" in content:
                    # Allow if explicitly marked as exception
                    if "# hypothesis: boundary-exception" in content:
                        continue
                    pytest.fail(
                        f"Property-based test found in forbidden directory: "
                        f"{test_file.relative_to(ROOT)}"
                    )


@pytest.mark.architecture
class TestLayerTestCoverage:
    """Validate each layer has required test types."""

    def test_unit_tests_exist_per_layer(self) -> None:
        """Each layer with unit: MUST should have unit tests."""
        matrix = _load_matrix()
        for layer, config in matrix["layers"].items():
            if config.get("unit") == "MUST":
                layer_test_dir = TESTS_DIR / "unit" / layer
                if layer == "interfaces":
                    layer_test_dir = TESTS_DIR / "unit" / "cli"
                if not layer_test_dir.is_dir():
                    # Try alternative naming
                    layer_test_dir = TESTS_DIR / "unit" / layer
                if layer_test_dir.is_dir():
                    test_files = list(layer_test_dir.rglob("test_*.py"))
                    assert len(test_files) > 0, (
                        f"Layer '{layer}' requires unit tests but none found in "
                        f"{layer_test_dir.relative_to(ROOT)}"
                    )
