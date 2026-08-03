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
"""Architecture guard for curated source-to-test ownership inventory."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src" / "bioetl"
TEST_ROOT = ROOT / "tests" / "unit"
INVENTORY_PATH = ROOT / "configs" / "quality" / "source_test_owner_inventory.yaml"
ALLOWED_OWNERSHIP = frozenset({"direct_test", "cluster_owner"})
ALLOWED_PREFIXES = (
    "src/bioetl/application/core/",
    "src/bioetl/application/composite/",
    "src/bioetl/application/services/control_plane/",
    "src/bioetl/infrastructure/adapters/",
    "src/bioetl/infrastructure/storage/",
)


def _load_inventory() -> dict[str, object]:
    with INVENTORY_PATH.open(encoding="utf-8") as inventory_file:
        payload = yaml.safe_load(inventory_file) or {}
    assert isinstance(payload, dict), (
        "source_test_owner_inventory.yaml must be a mapping"
    )
    return payload


def _expected_same_path_test(source_rel: str) -> str:
    source_path = ROOT / source_rel
    relative_source = source_path.relative_to(SRC_ROOT)
    expected = TEST_ROOT / relative_source.parent / f"test_{source_path.stem}.py"
    return expected.relative_to(ROOT).as_posix()


@pytest.mark.architecture
def test_curated_source_test_owner_inventory_has_expected_shape() -> None:
    payload = _load_inventory()
    assert payload.get("version"), (
        "Missing version in curated source-test owner inventory"
    )
    assert payload.get("policy_scope") == "curated_behavior_heavy_modules"

    modules = payload.get("modules")
    assert isinstance(modules, list) and modules, (
        "Curated source-test owner inventory must contain module rows"
    )

    for row in modules:
        assert isinstance(row, dict), "Each curated ownership row must be a mapping"
        assert row.get("source"), "Missing source in curated ownership row"
        assert row.get("ownership") in ALLOWED_OWNERSHIP, (
            f"Unsupported ownership type for {row.get('source')}: {row.get('ownership')}"
        )
        assert row.get("rationale"), f"Missing rationale for {row.get('source')}"
        owner_tests = row.get("owner_tests")
        assert isinstance(owner_tests, list) and owner_tests, (
            f"Missing owner_tests for {row.get('source')}"
        )


@pytest.mark.architecture
def test_curated_source_test_owner_inventory_references_existing_files() -> None:
    payload = _load_inventory()

    for row in payload["modules"]:
        source_rel = str(row["source"])
        source_path = ROOT / source_rel
        assert source_path.exists(), (
            f"Curated ownership source is missing: {source_rel}"
        )
        assert source_rel.startswith(ALLOWED_PREFIXES), (
            "Curated ownership inventory should stay limited to the RF-FS-004 "
            f"behavior-heavy scope: {source_rel}"
        )
        for owner_rel in row["owner_tests"]:
            owner_path = ROOT / owner_rel
            assert owner_path.exists(), (
                f"Owner test listed for {source_rel} does not exist: {owner_rel}"
            )


@pytest.mark.architecture
def test_curated_direct_test_rows_have_same_path_owner_tests() -> None:
    payload = _load_inventory()
    mismatches: list[str] = []

    for row in payload["modules"]:
        if row["ownership"] != "direct_test":
            continue
        source_rel = str(row["source"])
        expected_owner = _expected_same_path_test(source_rel)
        if expected_owner not in row["owner_tests"]:
            mismatches.append(f"{source_rel} -> expected {expected_owner}")

    assert not mismatches, (
        "Direct-test ownership rows must point to same-path test files.\n"
        + "\n".join(mismatches)
    )


@pytest.mark.architecture
def test_curated_cluster_owner_rows_do_not_require_same_path_mirror() -> None:
    payload = _load_inventory()

    for row in payload["modules"]:
        if row["ownership"] != "cluster_owner":
            continue
        source_rel = str(row["source"])
        expected_owner = _expected_same_path_test(source_rel)
        assert expected_owner not in row["owner_tests"], (
            "Cluster-owner rows should document aggregate/focused owner suites, "
            f"not same-path mirrors: {source_rel}"
        )
