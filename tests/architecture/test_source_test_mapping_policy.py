"""Architecture guard for staged source-to-test ownership policy."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src" / "bioetl"
TEST_ROOT = ROOT / "tests" / "unit"
INVENTORY_PATH = ROOT / "configs" / "quality" / "source_test_mapping_exceptions.yaml"


def _load_inventory(config_yaml_cache: dict[Path, object]) -> dict[str, object]:
    payload = config_yaml_cache.get(INVENTORY_PATH) or {}
    assert isinstance(payload, dict), (
        "source_test_mapping_exceptions.yaml must be a mapping"
    )
    return payload


def _iter_thin_package_modules() -> list[Path]:
    thin_modules: list[Path] = []
    for init_path in sorted(SRC_ROOT.rglob("__init__.py")):
        package_dir = init_path.parent
        py_files = sorted(
            path
            for path in package_dir.iterdir()
            if path.is_file() and path.suffix == ".py" and path.name != "__init__.py"
        )
        if len(py_files) == 1:
            thin_modules.append(py_files[0])
    return thin_modules


def _expected_same_path_test(source_path: Path) -> Path:
    relative_source = source_path.relative_to(SRC_ROOT)
    return TEST_ROOT / relative_source.parent / f"test_{source_path.stem}.py"


@pytest.mark.architecture
def test_source_test_mapping_inventory_exists_and_has_shape(
    config_yaml_cache: dict[Path, object],
) -> None:
    payload = _load_inventory(config_yaml_cache)
    assert payload.get("version"), "Missing version in source-test mapping inventory"
    assert payload.get("policy_scope") == "thin_packages"

    exemptions = payload.get("exemptions")
    assert isinstance(exemptions, list), "Inventory exemptions must be a list"

    for row in exemptions:
        assert isinstance(row, dict), "Each exemption row must be a mapping"
        assert row.get("source"), "Missing source in exemption row"
        assert row.get("policy"), "Missing policy in exemption row"
        assert row.get("reason"), "Missing reason in exemption row"
        owner_tests = row.get("owner_tests")
        assert isinstance(owner_tests, list) and owner_tests, (
            "Each exemption row must list canonical owner tests"
        )


@pytest.mark.architecture
def test_thin_package_modules_have_same_path_tests_or_documented_exemption(
    config_yaml_cache: dict[Path, object],
) -> None:
    payload = _load_inventory(config_yaml_cache)
    exemptions = {
        str(row["source"]): row
        for row in payload.get("exemptions", [])
        if isinstance(row, dict) and row.get("source")
    }

    missing: list[str] = []

    for source_path in _iter_thin_package_modules():
        source_rel = source_path.relative_to(ROOT).as_posix()
        expected_test = _expected_same_path_test(source_path)
        if expected_test.exists():
            continue
        if source_rel in exemptions:
            continue
        missing.append(f"{source_rel} -> {expected_test.relative_to(ROOT).as_posix()}")

    assert not missing, (
        "Thin-package source modules must have a same-path owner test or a "
        "documented exemption.\n" + "\n".join(missing)
    )


@pytest.mark.architecture
def test_source_test_mapping_exemptions_reference_existing_files(
    config_yaml_cache: dict[Path, object],
) -> None:
    payload = _load_inventory(config_yaml_cache)
    thin_sources = {
        path.relative_to(ROOT).as_posix() for path in _iter_thin_package_modules()
    }

    stale_entries: list[str] = []
    wrong_scope_entries: list[str] = []

    for row in payload.get("exemptions", []):
        if not isinstance(row, dict):
            continue
        source_rel = str(row["source"])
        source_path = ROOT / source_rel
        if not source_path.exists():
            stale_entries.append(source_rel)
            continue
        if source_rel not in thin_sources:
            wrong_scope_entries.append(source_rel)
        for owner_rel in row["owner_tests"]:
            owner_path = ROOT / owner_rel
            assert owner_path.exists(), (
                f"Owner test listed for {source_rel} does not exist: {owner_rel}"
            )

    assert not stale_entries, (
        "Source-test mapping inventory references missing source files:\n"
        + "\n".join(stale_entries)
    )
    assert not wrong_scope_entries, (
        "Thin-package source-test mapping inventory should only list thin-package "
        "modules:\n" + "\n".join(wrong_scope_entries)
    )
