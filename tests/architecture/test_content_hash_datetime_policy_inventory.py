"""Architecture guard for timestamp-sensitive content-hash datetime policy."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import yaml

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "configs" / "quality" / "determinism_identity_policy.yaml"


def _load_yaml(path: Path) -> dict[str, object]:
    return cast(dict[str, object], yaml.safe_load(path.read_text(encoding="utf-8")))


def test_timestamp_sensitive_hash_policy_inventory_matches_entity_configs() -> None:
    policy = _load_yaml(POLICY_PATH)
    hash_policy = cast(dict[str, object], policy["content_hash_datetime_policy"])
    inventory = cast(
        list[dict[str, object]],
        hash_policy.get("timestamp_sensitive_entity_inventory", []),
    )
    assert inventory, "Timestamp-sensitive content-hash policy inventory is empty"

    for item in inventory:
        provider = str(item["provider"])
        entity = str(item["entity"])
        expected_policy = str(item["configured_policy"])
        config = _load_yaml(ROOT / "configs" / "entities" / provider / f"{entity}.yaml")
        contracts = cast(dict[str, object], config.get("contracts", {}))
        assert contracts.get("hash_datetime_policy") == expected_policy, (
            f"{provider}.{entity} must declare "
            f"contracts.hash_datetime_policy={expected_policy}"
        )


def test_hash_datetime_policy_values_are_known() -> None:
    allowed = {"v1_date", "v2_datetime_utc"}
    for config_path in (ROOT / "configs" / "entities").rglob("*.yaml"):
        config = _load_yaml(config_path)
        contracts = config.get("contracts")
        if not isinstance(contracts, dict) or "hash_datetime_policy" not in contracts:
            continue
        value = str(contracts["hash_datetime_policy"])
        assert value in allowed, (
            f"{config_path.relative_to(ROOT)}: unsupported "
            f"contracts.hash_datetime_policy={value!r}"
        )
