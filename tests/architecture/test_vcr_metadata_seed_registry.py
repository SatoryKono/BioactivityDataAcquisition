"""Architecture guards for the current seeded VCR metadata sidecar slice."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = ROOT / "configs" / "quality" / "test_matrix.yaml"
VCR_ROOT = ROOT / "tests" / "fixtures" / "vcr"
YamlMap = dict[str, Any]


def _load_yaml(path: Path) -> YamlMap:
    with path.open(encoding="utf-8") as handle:
        return cast(YamlMap, yaml.safe_load(handle))


def _load_matrix() -> YamlMap:
    return _load_yaml(MATRIX_PATH)


def _fixture_governance(matrix: YamlMap) -> YamlMap:
    return cast(YamlMap, matrix.get("fixture_governance", {}))


def _seed_registry(matrix: YamlMap) -> YamlMap:
    fixture_governance = _fixture_governance(matrix)
    return cast(YamlMap, fixture_governance["cassette_metadata_seed_registry"])


def _tracked_sidecars(registry: YamlMap) -> list[str]:
    return cast(list[str], registry["tracked_sidecars"])


def _expected_provider_counts(registry: YamlMap) -> dict[str, int]:
    return cast(dict[str, int], registry["provider_expected_sidecar_counts"])


def _vcr_required_providers(matrix: YamlMap) -> set[str]:
    providers = cast(YamlMap, matrix.get("providers", {}))
    return {
        provider
        for provider, config in providers.items()
        if isinstance(provider, str)
        and isinstance(config, dict)
        and config.get("vcr_cassettes") == "MUST"
    }


@pytest.mark.architecture
class TestVcrMetadataSeedRegistry:
    """Keep the partial metadata sidecar rollout tied to an explicit managed slice."""

    def test_matrix_declares_current_seeded_sidecar_slice(self) -> None:
        matrix = _load_matrix()
        registry = _seed_registry(matrix)
        tracked_sidecars = _tracked_sidecars(registry)
        actual_sidecars = sorted(
            path.relative_to(ROOT).as_posix() for path in VCR_ROOT.rglob("*_meta.yaml")
        )

        assert registry.get("scope") == "bounded_provider_seed_slice"
        assert tracked_sidecars == actual_sidecars

    def test_seed_registry_covers_every_vcr_managed_provider(self) -> None:
        matrix = _load_matrix()
        registry = _seed_registry(matrix)
        tracked_providers = {
            (ROOT / relative_path).relative_to(VCR_ROOT).parts[0]
            for relative_path in _tracked_sidecars(registry)
        }

        assert registry.get("provider_coverage_mode") == "at_least_one_per_vcr_provider"
        assert tracked_providers == _vcr_required_providers(matrix)

    def test_seed_registry_declares_expected_provider_counts(self) -> None:
        matrix = _load_matrix()
        registry = _seed_registry(matrix)
        expected_counts = _expected_provider_counts(registry)
        actual_counts: dict[str, int] = {}
        for relative_path in _tracked_sidecars(registry):
            provider = (ROOT / relative_path).relative_to(VCR_ROOT).parts[0]
            actual_counts[provider] = actual_counts.get(provider, 0) + 1

        assert expected_counts == actual_counts

    def test_seeded_sidecars_match_backfill_payload_contract(self) -> None:
        matrix = _load_matrix()
        fixture_governance = _fixture_governance(matrix)
        registry = _seed_registry(matrix)
        expected_source = Path(
            cast(str, fixture_governance["cassette_metadata_backfill_script"])
        ).name

        for relative_path in _tracked_sidecars(registry):
            metadata_path = ROOT / relative_path
            payload = _load_yaml(metadata_path)
            provider = metadata_path.relative_to(VCR_ROOT).parts[0]
            cassette_rel_path = cast(str, payload["cassette_rel_path"])
            cassette_path = ROOT / cassette_rel_path

            assert metadata_path.exists()
            assert payload["schema_version"] == 1
            assert payload["provider"] == provider
            assert payload["metadata_status"] == "seeded_partial_backfill"
            assert payload["source"] == expected_source
            assert payload["staleness_ready"] is False
            assert cassette_path.exists()
            assert metadata_path == cassette_path.with_name(
                f"{cassette_path.stem}_meta.yaml"
            )

    def test_seed_registry_counts_match_catalog_summary(self) -> None:
        matrix = _load_matrix()
        registry = _seed_registry(matrix)
        expected_counts = _expected_provider_counts(registry)
        catalog_path = ROOT / "reports/quality/vcr-metadata-catalog.json"
        catalog = cast(YamlMap, json.loads(catalog_path.read_text(encoding="utf-8")))
        totals = cast(YamlMap, catalog["totals"])
        providers = cast(YamlMap, catalog["providers"])

        assert totals["metadata_sidecar_count"] == sum(expected_counts.values())

        for provider, expected_count in expected_counts.items():
            provider_summary = cast(YamlMap, providers[provider])
            assert provider_summary["metadata_sidecar_count"] == expected_count
