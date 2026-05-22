"""Architecture guardrails for compatibility importer census governance."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts.engineering.qa.import_graph_inventory import (
    collect_exact_module_import_usage,
)
from scripts.engineering.qa.report_compatibility_importer_census import (
    _render_markdown,
    build_compatibility_importer_census,
)

ROOT = Path(__file__).resolve().parents[2]
REPORT_JSON = ROOT / "reports" / "quality" / "compatibility-importer-census.json"
REPORT_MD = ROOT / "reports" / "quality" / "compatibility-importer-census.md"
TWIN_RATCHET = ROOT / "configs" / "quality" / "compatibility_twin_module_ratchet.yaml"
CONFIG_ROOT_FACADE = (
    ROOT / "configs" / "quality" / "infrastructure_config_root_facade_inventory.yaml"
)
REMOVED_COMPATIBILITY_MODULES = {
    "bioetl.infrastructure.storage.silver.operations.metadata_sidecar_adapter",
    "bioetl.application.services.checkpoint_compatibility_service_v2",
    "bioetl.domain.normalization.legacy_fingerprints",
}


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


@pytest.mark.architecture
def test_tracked_twin_family_ratchet_matches_live_census() -> None:
    """Tracked twin-family ratchet rows must match the live importer census."""
    payload = build_compatibility_importer_census(ROOT, snapshot_date="2026-05-20")
    tracked_rows = payload["tracked_twin_families"]
    assert isinstance(tracked_rows, list)
    live_rows = {
        str(row["family_id"]): row for row in tracked_rows if isinstance(row, dict)
    }

    inventory = _load_yaml(TWIN_RATCHET)
    assert inventory.get("linked_issue") == "#4452"
    families = inventory.get("families")
    assert isinstance(families, list)
    assert set(live_rows) == {
        str(row["family_id"]) for row in families if isinstance(row, dict)
    }

    for row in families:
        assert isinstance(row, dict)
        live = live_rows[str(row["family_id"])]
        assert live["public_module"] == row["public_module"]
        assert live["private_module"] == row["private_module"]
        assert (
            live["canonical_first_party_module"] == row["canonical_first_party_module"]
        )
        assert (
            live["current_public_src_importer_count"] <= row["max_public_src_importers"]
        )
        assert (
            live["current_private_src_importer_count"]
            <= row["max_private_src_importers"]
        )


@pytest.mark.architecture
def test_infrastructure_config_root_facade_inventory_matches_live_src_importers() -> (
    None
):
    """The retained infrastructure.config root-facade inventory must stay allowlisted."""
    inventory = _load_yaml(CONFIG_ROOT_FACADE)
    assert inventory.get("linked_issue") == "#4453"
    target_module = inventory.get("target_module")
    assert isinstance(target_module, str)
    symbol_rows = inventory.get("symbols")
    assert isinstance(symbol_rows, list)

    usage = collect_exact_module_import_usage(ROOT, target_module)
    src_usage = usage["src"]
    current_paths_by_symbol: dict[str, set[str]] = {}
    for importer_path, imported_names in src_usage.items():
        for imported_name in imported_names:
            current_paths_by_symbol.setdefault(imported_name, set()).add(importer_path)

    configured_symbols = {
        str(row["symbol"]): row for row in symbol_rows if isinstance(row, dict)
    }
    assert set(current_paths_by_symbol) <= set(configured_symbols), (
        "New first-party infrastructure.config root-facade symbols were introduced "
        f"without inventory review: {sorted(set(current_paths_by_symbol) - set(configured_symbols))}"
    )

    for symbol_name, row in configured_symbols.items():
        current_paths = current_paths_by_symbol.get(symbol_name, set())
        prefixes = row.get("allowlisted_path_prefixes")
        assert isinstance(prefixes, list) and prefixes
        assert len(current_paths) <= int(row["max_src_importers"]), (
            f"{symbol_name} root-facade importers grew beyond the reviewed baseline: "
            f"{len(current_paths)} > {row['max_src_importers']}"
        )
        assert all(
            any(path.startswith(prefix) for prefix in prefixes)
            for path in current_paths
        ), (
            f"{symbol_name} root-facade importers escaped the allowlisted prefixes: "
            f"{sorted(current_paths)}"
        )


@pytest.mark.architecture
def test_removed_compatibility_surfaces_remain_absent_and_unimported() -> None:
    """Removed compatibility surfaces must stay absent from src and static imports."""
    payload = build_compatibility_importer_census(ROOT, snapshot_date="2026-05-21")
    removed_rows = payload["removed_compatibility_surfaces"]
    assert isinstance(removed_rows, list)
    rows_by_module = {
        str(row["module_name"]): row for row in removed_rows if isinstance(row, dict)
    }

    assert set(rows_by_module) == REMOVED_COMPATIBILITY_MODULES
    for module_name, row in rows_by_module.items():
        assert row["path_exists"] is False, module_name
        assert row["src_importer_count"] == 0, module_name
        assert row["test_importer_count"] == 0, module_name


@pytest.mark.architecture
def test_retained_public_export_facades_remain_unique_and_budgeted() -> None:
    """Retained public facades must keep one reviewed public-export resolution path."""
    payload = build_compatibility_importer_census(ROOT, snapshot_date="2026-05-21")
    rows = payload["retained_public_export_facades"]
    assert isinstance(rows, list) and rows

    for row in rows:
        assert isinstance(row, dict)
        assert row["public_export_count"] <= row["max_public_exports"], row["path"]
        assert row["duplicate_public_exports"] == [], row["path"]
        assert row["duplicate_lazy_export_keys"] == [], row["path"]
        assert row["orphan_lazy_export_keys"] == [], row["path"]
        assert row["orphan_dunder_getattr_exports"] == [], row["path"]
        assert row["resolution_conflicts"] == {}, row["path"]


@pytest.mark.architecture
def test_compatibility_importer_census_reports_are_in_sync() -> None:
    """Committed compatibility importer census JSON must match the generator."""
    committed_json = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
    expected_payload = build_compatibility_importer_census(
        ROOT,
        snapshot_date=str(committed_json["snapshot_date"]),
    )

    assert committed_json == expected_payload
    expected_markdown = _render_markdown(expected_payload)
    if REPORT_MD.exists():
        assert REPORT_MD.read_text(encoding="utf-8") == expected_markdown
