"""Architecture guard for canonical provider regression suites."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = ROOT / "configs" / "quality" / "test_matrix.yaml"


def _load_matrix() -> dict:
    """Load the test matrix configuration."""
    with MATRIX_PATH.open(encoding="utf-8") as file_obj:
        return yaml.safe_load(file_obj)


@pytest.mark.architecture
def test_provider_regression_suites_reference_known_providers_and_existing_files() -> (
    None
):
    """Canonical regression suites must stay aligned with matrix provider inventory."""
    matrix = _load_matrix()
    providers = set(matrix["providers"])
    regression_suites = matrix.get("provider_regression_suites", {})

    assert "metadata_request_capability" in regression_suites
    assert "slow_health_probe_policy" in regression_suites

    for suite_name, suite_config in regression_suites.items():
        provider_paths = suite_config.get("providers", {})
        assert provider_paths, (
            f"provider_regression_suites.{suite_name} must not be empty"
        )

        unknown_providers = sorted(set(provider_paths) - providers)
        assert not unknown_providers, (
            f"provider_regression_suites.{suite_name} references unknown providers: "
            f"{', '.join(unknown_providers)}"
        )

        for provider, relative_path in provider_paths.items():
            path = ROOT / relative_path
            assert relative_path.startswith("tests/"), (
                f"provider_regression_suites.{suite_name}.{provider} must point to a test path, "
                f"got: {relative_path}"
            )
            assert path.is_file(), (
                f"provider_regression_suites.{suite_name}.{provider} points to missing file: "
                f"{relative_path}"
            )
