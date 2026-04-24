"""Architecture guards for the managed VCR metadata inventory."""

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


def _inventory_contract(matrix: YamlMap) -> YamlMap:
    fixture_governance = _fixture_governance(matrix)
    return cast(YamlMap, fixture_governance["cassette_metadata_inventory_contract"])


def _expected_provider_counts(contract: YamlMap) -> dict[str, int]:
    return cast(dict[str, int], contract["provider_expected_sidecar_counts"])


def _cassette_files() -> list[Path]:
    return sorted(
        path
        for path in VCR_ROOT.rglob("*")
        if path.is_file()
        and path.suffix.lower() in {".yaml", ".yml"}
        and not path.name.endswith(("_meta.yaml", "_meta.yml"))
    )


def _metadata_files() -> list[Path]:
    return sorted(VCR_ROOT.rglob("*_meta.yaml"))


@pytest.mark.architecture
class TestVcrMetadataInventory:
    """Keep metadata backfill tied to the full managed VCR inventory."""

    def test_matrix_declares_managed_inventory_contract(self) -> None:
        matrix = _load_matrix()
        contract = _inventory_contract(matrix)
        actual_metadata = [path.relative_to(ROOT).as_posix() for path in _metadata_files()]

        assert contract.get("scope") == "managed_vcr_inventory"
        assert (
            contract.get("metadata_catalog_location")
            == "reports/quality/vcr-metadata-catalog.json"
        )
        assert (
            contract.get("stale_age_checker")
            == "scripts/engineering/qa/vcr/check_vcr_metadata_age.py"
        )
        assert len(actual_metadata) == sum(_expected_provider_counts(contract).values())

    def test_inventory_contract_covers_every_cassette_provider(self) -> None:
        matrix = _load_matrix()
        contract = _inventory_contract(matrix)
        expected_counts = _expected_provider_counts(contract)
        actual_counts: dict[str, int] = {}

        for cassette_path in _cassette_files():
            provider = cassette_path.relative_to(VCR_ROOT).parts[0]
            actual_counts[provider] = actual_counts.get(provider, 0) + 1

        assert expected_counts == actual_counts

    def test_every_managed_cassette_has_a_metadata_sidecar(self) -> None:
        expected_metadata_paths = {
            path.with_name(f"{path.stem}_meta.yaml").relative_to(ROOT).as_posix()
            for path in _cassette_files()
        }
        actual_metadata_paths = {
            path.relative_to(ROOT).as_posix() for path in _metadata_files()
        }

        assert expected_metadata_paths == actual_metadata_paths

    def test_managed_metadata_inventory_matches_catalog_summary(self) -> None:
        matrix = _load_matrix()
        contract = _inventory_contract(matrix)
        expected_counts = _expected_provider_counts(contract)
        catalog_path = ROOT / contract["metadata_catalog_location"]
        catalog = cast(YamlMap, json.loads(catalog_path.read_text(encoding="utf-8")))
        totals = cast(YamlMap, catalog["totals"])
        providers = cast(YamlMap, catalog["providers"])

        cassette_count = len(_cassette_files())
        metadata_count = len(_metadata_files())
        assert totals["cassette_count"] == cassette_count
        assert totals["metadata_sidecar_count"] == metadata_count
        assert metadata_count == cassette_count

        for provider, expected_count in expected_counts.items():
            provider_summary = cast(YamlMap, providers[provider])
            assert provider_summary["cassette_count"] == expected_count
            assert provider_summary["metadata_sidecar_count"] == expected_count
            assert provider_summary["without_metadata_count"] == 0
            assert provider_summary["metadata_coverage_percent"] == 100.0
