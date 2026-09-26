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
"""Config-surface classification and validation-ownership guardrails."""

from __future__ import annotations

import pytest

from pathlib import Path

import yaml

from scripts.schema.analysis import config_gap_analysis, generate_config_matrix


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = ROOT / "configs" / "quality" / "config_validation_surface.yaml"
CONFIG_ROOT = ROOT / "configs"
SUPPORTED_SUFFIXES = {".yaml", ".json", ".csv", ".md"}
VALIDATION_DEPTHS = {
    "documentation",
    "governance_gate",
    "inventory_only",
    "schema_level",
    "semantic",
    "snapshot",
    "cross_file",
}


def _load_inventory() -> dict[str, object]:
    payload = yaml.safe_load(INVENTORY_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), "config validation inventory must be a mapping"
    return payload


def _tracked_config_files() -> list[str]:
    return sorted(
        path.relative_to(ROOT).as_posix()
        for path in CONFIG_ROOT.rglob("*")
        if path.is_file() and path.suffix in SUPPORTED_SUFFIXES
    )


def _family_prefixes(inventory: dict[str, object]) -> dict[str, str]:
    families = inventory.get("families")
    assert isinstance(families, list) and families, "families must be non-empty"
    prefixes: dict[str, str] = {}
    seen_family_ids: set[str] = set()
    for family in families:
        assert isinstance(family, dict), "each family must be a mapping"
        family_id = family.get("family_id")
        assert isinstance(family_id, str) and family_id
        assert family_id not in seen_family_ids, f"duplicate family_id: {family_id}"
        seen_family_ids.add(family_id)
        assert isinstance(family.get("owner"), str) and family["owner"]
        assert (
            isinstance(family.get("validation_mechanism"), str)
            and family["validation_mechanism"]
        )
        validation_depth = family.get("validation_depth")
        assert isinstance(validation_depth, str) and validation_depth, (
            f"{family_id} must declare validation_depth"
        )
        assert validation_depth in VALIDATION_DEPTHS, (
            f"{family_id} declares unsupported validation_depth={validation_depth!r}"
        )
        if validation_depth == "inventory_only":
            rationale = family.get("inventory_only_rationale") or family.get(
                "depth_rationale"
            )
            assert isinstance(rationale, str) and rationale.strip(), (
                f"{family_id} inventory-only validation requires rationale"
            )
        if validation_depth in {"inventory_only", "snapshot"}:
            rationale = family.get("depth_rationale") or family.get(
                "inventory_only_rationale"
            )
            assert isinstance(rationale, str) and rationale.strip(), (
                f"{family_id} {validation_depth} validation requires rationale"
            )
            migration_path = family.get("migration_path")
            assert isinstance(migration_path, str) and migration_path.strip(), (
                f"{family_id} {validation_depth} validation requires migration_path"
            )
        enforcing_surfaces = family.get("enforcing_surfaces")
        assert isinstance(enforcing_surfaces, list) and enforcing_surfaces
        for prefix in family.get("path_prefixes", []):
            assert isinstance(prefix, str) and prefix
            assert prefix not in prefixes, f"duplicate config path prefix: {prefix}"
            prefixes[prefix] = family_id
    return prefixes


def test_every_config_file_is_classified_by_validation_surface() -> None:
    inventory = _load_inventory()
    prefixes = _family_prefixes(inventory)
    classified: dict[str, str] = {}
    unclassified: list[str] = []

    for config_file in _tracked_config_files():
        matched = [
            family
            for prefix, family in prefixes.items()
            if config_file.startswith(prefix)
        ]
        if not matched:
            unclassified.append(config_file)
            continue
        assert len(matched) == 1, (
            f"{config_file} matches multiple config families: {matched}"
        )
        classified[config_file] = matched[0]

    assert not unclassified, (
        "Every config file must declare validation ownership in "
        f"{INVENTORY_PATH.relative_to(ROOT)}; missing={unclassified}"
    )
    assert classified, "Expected at least one classified config file"


def test_config_validation_inventory_is_self_classified() -> None:
    inventory = _load_inventory()
    prefixes = _family_prefixes(inventory)
    relative_path = INVENTORY_PATH.relative_to(ROOT).as_posix()

    assert any(relative_path.startswith(prefix) for prefix in prefixes)


def test_validate_configs_reports_validation_depth_summary() -> None:
    script = (
        ROOT / "scripts" / "schema" / "validation" / "validate_pipeline_configs.py"
    ).read_text(encoding="utf-8")

    assert "_emit_validation_depth_summary(configs_root)" in script
    assert "Config validation surface family depths" in script


def test_ai_docs_validate_configs_legacy_wrappers_stay_retired() -> None:
    live_wrapper = (
        ROOT
        / "docs"
        / "00-project"
        / "ai"
        / "agents"
        / "scripts"
        / "py-config-bot-2.py"
    )
    assert not live_wrapper.exists()
    archived_wrapper = (
        ROOT / "docs" / "99-archive" / "agents-scripts-2026-09" / "py-config-bot-2.py"
    )
    assert not archived_wrapper.exists()

    canonical_validator = (
        ROOT / "scripts" / "schema" / "validation" / "validate_pipeline_configs.py"
    )
    assert canonical_validator.is_file()


def test_py_config_bot_gap_analysis_uses_canonical_composite_runtime_configs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Legacy entity composite stubs must not be re-audited as standard configs."""
    monkeypatch.chdir(ROOT)

    config_names = set(generate_config_matrix._collect_configs())

    assert "composite/molecule" in config_names
    assert not any(name.startswith("entity/composite/") for name in config_names)


def test_config_gap_analysis_uses_canonical_composite_runtime_configs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The maintained gap analyzer must not scan retired entity composite stubs."""
    monkeypatch.chdir(ROOT)

    config_paths = {
        path.as_posix() for path in config_gap_analysis._iter_config_files()
    }

    assert "configs/composites/molecule.yaml" in config_paths
    assert not any(
        path.startswith("configs/entities/composite/") for path in config_paths
    )


def test_high_risk_runtime_config_families_require_cross_file_validation() -> None:
    inventory = _load_inventory()
    families = inventory.get("families")
    assert isinstance(families, list)

    expected_depths = {
        "composite_runtime": "cross_file",
        "entity_pipelines": "cross_file",
        "provider_runtime": "cross_file",
        "workflow_runtime": "cross_file",
    }
    observed_depths = {
        family["family_id"]: family["validation_depth"]
        for family in families
        if isinstance(family, dict)
        and isinstance(family.get("family_id"), str)
        and isinstance(family.get("validation_depth"), str)
    }

    for family_id, expected_depth in expected_depths.items():
        assert observed_depths.get(family_id) == expected_depth, (
            f"{family_id} must declare {expected_depth} validation depth"
        )
