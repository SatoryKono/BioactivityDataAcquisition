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
"""Architecture guardrails for compatibility importer census governance."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.architecture._platform_skip_support import mounted_worktree_skip_reason

# Skip on WSL and Windows due to filesystem performance causing git command timeout
pytestmark = [pytest.mark.timeout(300)]
if (skip_reason := mounted_worktree_skip_reason()) is not None:
    pytestmark.append(pytest.mark.skip(reason=skip_reason))

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
CONTROL_PLANE_ROOT_FACADE = (
    ROOT
    / "configs"
    / "quality"
    / "application_control_plane_root_facade_inventory.yaml"
)
REMOVED_COMPATIBILITY_MODULES = {
    "bioetl.application.services.control_plane.historical_replay_certification_service",
    "bioetl.application.services.control_plane.historical_replay_closure_models",
    "bioetl.application.services.control_plane.historical_replay_closure_policy",
    "bioetl.application.services.control_plane.historical_replay_closure_service",
    "bioetl.application.services.control_plane.historical_replay_corpus_models",
    "bioetl.application.services.control_plane.historical_replay_corpus_policy",
    "bioetl.application.services.control_plane.historical_replay_corpus_service",
    "bioetl.application.services.control_plane.historical_replay_universe_policy",
    "bioetl.application.services.control_plane.historical_replay_universe_service",
    "bioetl.application.services.control_plane.replay_bundle_descriptor_service",
    "bioetl.application.services.control_plane.run_manifest_diagnostics",
    "bioetl.application.services.control_plane.run_manifest_inspection_service",
    "bioetl.application.services.control_plane.run_manifest_replay_taxonomy",
    "bioetl.application.services.control_plane.workflow_execution_preparation",
    "bioetl.application.services.control_plane.workflow_execution_recording",
    "bioetl.application.services.control_plane.workflow_execution_service",
    "bioetl.application.services.control_plane.workflow_inspection_service",
    "bioetl.application.services.control_plane.workflow_ledger_service",
    "bioetl.application.services.control_plane.workflow_manifest_models",
    "bioetl.application.services.control_plane.workflow_manifest_service",
    "bioetl.infrastructure.storage.silver.operations.metadata_sidecar_adapter",
    "bioetl.application.services.checkpoint_compatibility_service_v2",
    "bioetl.domain.normalization.legacy_fingerprints",
}


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _module_to_src_path(module_name: str) -> str:
    relative = "/".join(module_name.split(".")[1:])
    return f"src/bioetl/{relative}.py"


def _git_command(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )


def _resolve_merge_base(repo_root: Path) -> str | None:
    for ref in ("origin/main", "main"):
        if _git_command(repo_root, "rev-parse", "--verify", ref).returncode != 0:
            continue
        merge = _git_command(repo_root, "merge-base", "HEAD", ref)
        if merge.returncode == 0:
            return merge.stdout.strip() or None
    return None


def _collect_changed_repo_paths(repo_root: Path) -> set[str]:
    changed: set[str] = set()
    merge_base = _resolve_merge_base(repo_root)
    if merge_base is not None:
        diff = _git_command(repo_root, "diff", "--name-only", merge_base, "HEAD")
        if diff.returncode == 0:
            changed.update(
                line.strip() for line in diff.stdout.splitlines() if line.strip()
            )
    for args in (
        ("diff", "--name-only", "HEAD"),
        ("diff", "--name-only", "--cached", "HEAD"),
    ):
        diff = _git_command(repo_root, *args)
        if diff.returncode == 0:
            changed.update(
                line.strip() for line in diff.stdout.splitlines() if line.strip()
            )
    return changed


def _family_touch_surface(
    family_row: dict[str, Any],
    *,
    importer_source: dict[str, Any] | None = None,
) -> set[str]:
    """Resolve touch_policy categories to concrete repo paths for a twin family."""
    source = importer_source if importer_source is not None else family_row
    surface = {
        _module_to_src_path(str(family_row["public_module"])),
        _module_to_src_path(str(family_row["private_module"])),
    }
    for key in ("current_public_src_importers", "current_private_src_importers"):
        importers = source.get(key)
        if isinstance(importers, list):
            surface.update(str(path) for path in importers)
    return surface


def _ratchet_family_budgets(
    ratchet_payload: dict[str, Any],
) -> dict[str, dict[str, int]]:
    families = ratchet_payload.get("families")
    assert isinstance(families, list)
    budgets: dict[str, dict[str, int]] = {}
    for row in families:
        if not isinstance(row, dict):
            continue
        family_id = str(row["family_id"])
        budgets[family_id] = {
            "max_public_src_importers": int(row["max_public_src_importers"]),
            "max_private_src_importers": int(row["max_private_src_importers"]),
        }
    return budgets


@pytest.mark.architecture
def test_tracked_twin_family_ratchet_declares_touch_no_growth_policy() -> None:
    """Twin-family ratchet metadata must declare the touch-based no-growth gate."""
    inventory = _load_yaml(TWIN_RATCHET)
    touch_policy = inventory.get("touch_policy")
    assert isinstance(touch_policy, dict)
    assert touch_policy.get("linked_issue") == "#4827"
    assert touch_policy.get("mode") == "fail-fast-no-growth-on-touch"
    assert touch_policy.get("baseline_artifact") == (
        "reports/quality/compatibility-importer-census.json"
    )
    assert touch_policy.get("expected_direction") == "downward"
    assert set(touch_policy.get("touch_surface", [])) == {
        "twin_module_paths",
        "tracked_src_importers",
    }
    assert str(touch_policy.get("rationale", "")).strip()


@pytest.mark.architecture
def test_touched_twin_family_files_do_not_grow_private_imports() -> None:
    """Touched twin-family surfaces must not grow private-module imports past baseline."""
    changed_paths = _collect_changed_repo_paths(ROOT)
    if not changed_paths:
        return

    baseline_payload = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
    baseline_rows = baseline_payload["tracked_twin_families"]
    assert isinstance(baseline_rows, list)
    ratchet_budgets = _ratchet_family_budgets(_load_yaml(TWIN_RATCHET))

    live_payload = build_compatibility_importer_census(
        ROOT,
        snapshot_date=str(baseline_payload["snapshot_date"]),
    )
    live_rows = {
        str(row["family_id"]): row
        for row in live_payload["tracked_twin_families"]
        if isinstance(row, dict)
    }

    violations: list[str] = []
    for baseline_row in baseline_rows:
        if not isinstance(baseline_row, dict):
            continue
        family_id = str(baseline_row["family_id"])
        live_row = live_rows[family_id]
        touch_surface = _family_touch_surface(
            baseline_row,
            importer_source=live_row,
        )
        if not touch_surface.intersection(changed_paths):
            continue

        baseline_private_importers = {
            str(path) for path in baseline_row.get("current_private_src_importers", [])
        }
        live_private_importers = {
            str(path) for path in live_row.get("current_private_src_importers", [])
        }
        baseline_count = int(baseline_row["current_private_src_importer_count"])
        live_count = int(live_row["current_private_src_importer_count"])
        max_private = ratchet_budgets[family_id]["max_private_src_importers"]

        new_private_importers = sorted(
            live_private_importers - baseline_private_importers
        )
        if live_count > max_private:
            violations.append(
                f"{family_id}: private src importers {live_count} exceed ratchet "
                f"budget {max_private} after touching "
                f"{sorted(touch_surface & changed_paths)}"
            )
            continue
        if live_count > baseline_count:
            violations.append(
                f"{family_id}: private src importers grew from {baseline_count} to "
                f"{live_count} after touching "
                f"{sorted(touch_surface & changed_paths)}; refresh the census "
                "baseline only with an explicit ratchet review"
            )
            continue
        if new_private_importers:
            violations.append(
                f"{family_id}: new private-module importers detected after touch: "
                f"{new_private_importers}"
            )

    assert not violations, (
        "Twin-family touch gate blocked private import growth:\n"
        + "\n".join(f"  - {item}" for item in violations)
    )


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
    assert inventory.get("linked_issue") == "#4744"
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
    assert inventory.get("linked_issue") == "#5490"
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
def test_application_control_plane_root_facade_stays_zero_first_party_src() -> None:
    """The control-plane package root must stay external-only for first-party code."""
    inventory = _load_yaml(CONTROL_PLANE_ROOT_FACADE)
    assert inventory.get("linked_issue") == "#5510"
    assert inventory.get("new_src_import_policy") == (
        "external_only_zero_first_party_growth"
    )
    target_module = inventory.get("target_module")
    assert isinstance(target_module, str)

    usage = collect_exact_module_import_usage(ROOT, target_module)
    assert usage["src"] == {}, (
        "New first-party imports of the control-plane package root were detected: "
        f"{sorted(usage['src'])}"
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
def test_narrow_first_party_retained_entrypoints_do_not_gain_src_importers() -> None:
    """Narrow-first-party retained seams must stay confined to owner import paths."""
    payload = build_compatibility_importer_census(ROOT, snapshot_date="2026-06-02")
    rows = {
        str(row["path"]): row
        for row in payload["retained_entrypoints"]
        if isinstance(row, dict)
    }
    expected_src_importers = {
        "src/bioetl/composition/health_api.py": set(),
        "src/bioetl/composition/maintenance_api.py": set(),
    }

    violations: list[str] = []
    for path, expected in expected_src_importers.items():
        row = rows[path]
        actual = set(row["src_importers"])
        if actual != expected:
            violations.append(
                f"{path}: expected src importers {sorted(expected)}, "
                f"got {sorted(actual)}"
            )

    assert not violations, (
        "Narrow-first-party retained entrypoint importer budget drifted:\n"
        + "\n".join(f"  - {item}" for item in violations)
    )


@pytest.mark.architecture
def test_retained_entrypoint_owner_usage_map_is_published() -> None:
    payload = build_compatibility_importer_census(ROOT, snapshot_date="2026-06-19")
    rows = payload["retained_entrypoint_owner_usage_map"]
    assert isinstance(rows, list) and rows

    by_path = {str(row["path"]): row for row in rows if isinstance(row, dict)}
    config_root = by_path["src/bioetl/infrastructure/config/__init__.py"]
    assert config_root["surface_classification"] == "external-facing"
    maintenance_api = by_path["src/bioetl/composition/maintenance_api.py"]
    assert maintenance_api["owner"] == "bioetl.composition"
    assert maintenance_api["usage_classification"] == (
        "stable_public_api_with_reviewed_first_party_usage"
    )
    assert maintenance_api["surface_classification"] == "external-facing"
    assert maintenance_api["src_importer_count"] == 0
    assert maintenance_api["test_importer_count"] == 1
    assert payload["summary"]["control_plane_root_src_importer_count"] == 0


@pytest.mark.architecture
def test_retained_public_export_owner_usage_map_is_published() -> None:
    payload = build_compatibility_importer_census(ROOT, snapshot_date="2026-06-19")
    rows = payload["retained_public_export_owner_usage_map"]
    assert isinstance(rows, list) and rows

    by_path = {str(row["path"]): row for row in rows if isinstance(row, dict)}
    entrypoints = by_path["src/bioetl/composition/entrypoints.py"]
    assert entrypoints["owner"] == "bioetl.composition"
    assert entrypoints["usage_classification"] == (
        "stable_public_api_zero_first_party_src"
    )
    assert entrypoints["public_export_count"] > 0


@pytest.mark.architecture
def test_first_safe_removal_wave_is_deferred_while_importers_remain() -> None:
    payload = build_compatibility_importer_census(ROOT, snapshot_date="2026-06-19")
    first_wave = payload["first_safe_removal_wave"]
    assert isinstance(first_wave, dict)
    assert first_wave["linked_issue"] == "#5485"
    assert first_wave["review_date"] == "2026-07-19"

    rows = first_wave["rows"]
    assert isinstance(rows, list) and rows
    by_path = {str(row["path"]): row for row in rows if isinstance(row, dict)}
    maintenance = by_path["src/bioetl/interfaces/cli/commands/maintenance.py"]
    assert maintenance["owner"] == "bioetl.interfaces.cli.commands"
    assert maintenance["surface_classification"] == "first-party-active"
    assert maintenance["src_importers"] == [
        "src/bioetl/interfaces/cli/commands/__init__.py",
        "src/bioetl/interfaces/cli/commands/domains/maintenance/__init__.py",
    ]
    assert maintenance["src_importer_count"] == 2
    assert maintenance["test_importer_count"] == 0
    assert maintenance["action"] == "defer_until_first_party_importers_zero"
    assert maintenance["migration_prerequisites"]


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
        assert row["missing_retained_wrappers_outside_all"] == [], row["path"]
        assert row["unexpected_retained_wrappers_outside_all"] == [], row["path"]
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
