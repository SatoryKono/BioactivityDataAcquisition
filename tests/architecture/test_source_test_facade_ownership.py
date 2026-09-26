# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Architecture guard for sanctioned facade source-to-test ownership."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src" / "bioetl"
TEST_ROOT = ROOT / "tests"
INVENTORY_PATH = ROOT / "configs" / "quality" / "source_test_facade_inventory.yaml"
CURATED_INVENTORY_PATH = (
    ROOT / "configs" / "quality" / "source_test_owner_inventory.yaml"
)
THIN_PACKAGE_INVENTORY_PATH = (
    ROOT / "configs" / "quality" / "source_test_mapping_exceptions.yaml"
)
ALLOWED_OWNERSHIP = frozenset({"facade_contract"})
ALLOWED_PREFIXES = (
    "src/bioetl/application/composite/",
    "src/bioetl/infrastructure/adapters/",
)
FACADE_MARKERS = (
    "facade",
    "stable canonical import path",
    "public api remains stable",
    "compatibility",
)


def _load_yaml(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as inventory_file:
        payload = yaml.safe_load(inventory_file) or {}
    assert isinstance(payload, dict), f"{path.name} must be a mapping"
    return payload


def _expected_same_path_test(source_rel: str) -> str:
    source_path = ROOT / source_rel
    relative_source = source_path.relative_to(SRC_ROOT)
    expected = (
        TEST_ROOT / "unit" / relative_source.parent / f"test_{source_path.stem}.py"
    )
    return expected.relative_to(ROOT).as_posix()


def _is_facade_like_module(source_path: Path) -> bool:
    if source_path.name == "__init__.py":
        return True
    content = source_path.read_text(encoding="utf-8").lower()
    return any(marker in content for marker in FACADE_MARKERS)


@pytest.mark.architecture
def test_source_test_facade_inventory_has_expected_shape() -> None:
    payload = _load_yaml(INVENTORY_PATH)
    assert payload.get("version"), "Missing version in source-test facade inventory"
    assert payload.get("policy_scope") == "facade_modules"

    modules = payload.get("modules")
    assert isinstance(modules, list) and modules, (
        "Source-test facade inventory must contain module rows"
    )

    for row in modules:
        assert isinstance(row, dict), "Each facade ownership row must be a mapping"
        assert row.get("source"), "Missing source in facade ownership row"
        assert row.get("ownership") in ALLOWED_OWNERSHIP, (
            f"Unsupported ownership type for {row.get('source')}: {row.get('ownership')}"
        )
        assert row.get("rationale"), f"Missing rationale for {row.get('source')}"
        owner_tests = row.get("owner_tests")
        assert isinstance(owner_tests, list) and owner_tests, (
            f"Missing owner_tests for {row.get('source')}"
        )


@pytest.mark.architecture
def test_source_test_facade_inventory_references_existing_files() -> None:
    payload = _load_yaml(INVENTORY_PATH)

    for row in payload["modules"]:
        source_rel = str(row["source"])
        source_path = ROOT / source_rel
        assert source_path.exists(), f"Facade ownership source is missing: {source_rel}"
        assert source_rel.startswith(ALLOWED_PREFIXES), (
            "Facade ownership inventory should stay limited to the staged "
            f"application/composite and infrastructure/adapters scope: {source_rel}"
        )
        assert _is_facade_like_module(source_path), (
            "Facade ownership inventory should only contain package facades or "
            f"explicit facade-like modules: {source_rel}"
        )
        for owner_rel in row["owner_tests"]:
            owner_path = ROOT / owner_rel
            assert owner_path.exists(), (
                f"Owner test listed for {source_rel} does not exist: {owner_rel}"
            )
            assert owner_rel.startswith(("tests/unit/", "tests/architecture/")), (
                "Facade ownership rows should point to unit or architecture "
                f"tests only: {owner_rel}"
            )


@pytest.mark.architecture
def test_source_test_facade_inventory_does_not_overlap_other_mapping_inventories() -> (
    None
):
    facade_payload = _load_yaml(INVENTORY_PATH)
    curated_payload = _load_yaml(CURATED_INVENTORY_PATH)
    thin_payload = _load_yaml(THIN_PACKAGE_INVENTORY_PATH)

    facade_sources = {str(row["source"]) for row in facade_payload["modules"]}
    curated_sources = {str(row["source"]) for row in curated_payload["modules"]}
    thin_sources = {
        str(row["source"])
        for row in thin_payload.get("exemptions", [])
        if isinstance(row, dict) and row.get("source")
    }

    overlap = sorted(
        (facade_sources & curated_sources) | (facade_sources & thin_sources)
    )
    assert not overlap, (
        "Facade ownership inventory must not duplicate sources already owned by "
        "thin-package or curated behavior-heavy inventories:\n" + "\n".join(overlap)
    )


@pytest.mark.architecture
def test_facade_rows_document_non_mirror_owner_tests() -> None:
    payload = _load_yaml(INVENTORY_PATH)
    mirror_owners: list[str] = []

    for row in payload["modules"]:
        source_rel = str(row["source"])
        source_path = ROOT / source_rel
        if source_path.name == "__init__.py":
            continue
        expected_owner = _expected_same_path_test(source_rel)
        if expected_owner in row["owner_tests"]:
            mirror_owners.append(f"{source_rel} -> {expected_owner}")

    assert not mirror_owners, (
        "Facade inventory is reserved for sanctioned non-mirror ownership rows.\n"
        + "\n".join(mirror_owners)
    )
