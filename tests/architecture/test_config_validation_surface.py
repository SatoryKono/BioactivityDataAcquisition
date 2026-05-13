"""Config-surface classification and validation-ownership guardrails."""

from __future__ import annotations

from pathlib import Path

import yaml


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
            rationale = family.get("inventory_only_rationale")
            assert isinstance(rationale, str) and rationale.strip(), (
                f"{family_id} inventory-only validation requires rationale"
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
        ROOT
        / "docs"
        / "00-project"
        / "ai"
        / "agents"
        / "scripts"
        / "py-config-bot-2.py"
    ).read_text(encoding="utf-8")

    assert "_emit_validation_depth_summary(configs_root)" in script
    assert "Config validation surface family depths" in script
