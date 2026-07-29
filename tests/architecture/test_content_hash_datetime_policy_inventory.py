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
"""Architecture guard for timestamp-sensitive content-hash datetime policy."""

from __future__ import annotations

import pytest

from pathlib import Path
import re
from typing import cast

import yaml

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "configs" / "quality" / "determinism_identity_policy.yaml"
DATE_FIELD_RE = re.compile(r"(date|time|timestamp|revis|creat|modif|updat)", re.I)


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


def test_date_only_hash_policy_inventory_matches_entity_configs() -> None:
    policy = _load_yaml(POLICY_PATH)
    hash_policy = cast(dict[str, object], policy["content_hash_datetime_policy"])
    inventory = cast(
        list[dict[str, object]],
        hash_policy.get("date_only_entity_inventory", []),
    )
    assert inventory == [], (
        "Residual date-only content-hash compatibility inventory must stay empty "
        "after the final v2_datetime_utc migration closeout"
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


def test_v1_date_hash_policy_is_inventory_gated() -> None:
    policy = _load_yaml(POLICY_PATH)
    hash_policy = cast(dict[str, object], policy["content_hash_datetime_policy"])
    date_only_inventory = {
        (str(item["provider"]), str(item["entity"]))
        for item in cast(
            list[dict[str, object]],
            hash_policy.get("date_only_entity_inventory", []),
        )
    }

    undeclared: list[str] = []
    for config_path in (ROOT / "configs" / "entities").rglob("*.yaml"):
        config = _load_yaml(config_path)
        contracts = config.get("contracts")
        if not isinstance(contracts, dict):
            continue
        if contracts.get("hash_datetime_policy") != "v1_date":
            continue
        provider = str(config.get("provider"))
        entity = str(config.get("entity"))
        if (provider, entity) not in date_only_inventory:
            undeclared.append(str(config_path.relative_to(ROOT)))

    assert not undeclared, (
        "v1_date hash datetime compatibility must be declared in "
        "determinism_identity_policy.yaml date_only_entity_inventory:\n"
        + "\n".join(undeclared)
    )


def test_low_risk_date_only_surfaces_stay_migrated_to_v2_default() -> None:
    policy = _load_yaml(POLICY_PATH)
    hash_policy = cast(dict[str, object], policy["content_hash_datetime_policy"])
    date_only_inventory = {
        (str(item["provider"]), str(item["entity"]))
        for item in cast(
            list[dict[str, object]],
            hash_policy.get("date_only_entity_inventory", []),
        )
    }
    migrated = {
        ("chembl", "activity"),
        ("chembl", "assay"),
        ("chembl", "assay_parameters"),
        ("chembl", "cell_line"),
        ("chembl", "compound_record"),
        ("chembl", "molecule"),
        ("chembl", "protein_class"),
        ("crossref", "publication"),
        ("openalex", "publication"),
        ("chembl", "publication_similarity"),
        ("chembl", "publication_term"),
        ("pubchem", "compound"),
        ("semanticscholar", "publication"),
        ("chembl", "subcellular_fraction"),
        ("chembl", "target"),
        ("chembl", "target_component"),
        ("chembl", "target_protein_classification"),
        ("chembl", "tissue"),
        ("uniprot", "idmapping"),
    }

    assert migrated.isdisjoint(date_only_inventory)

    for provider, entity in migrated:
        config = _load_yaml(ROOT / "configs" / "entities" / provider / f"{entity}.yaml")
        contracts = cast(dict[str, object], config.get("contracts", {}))
        assert contracts.get("hash_datetime_policy") == "v2_datetime_utc", (
            f"{provider}.{entity} must stay on the v2 default once removed from "
            "date-only compatibility inventory"
        )


def test_residual_v1_date_inventory_requires_date_like_hash_fields() -> None:
    """Residual v1_date inventory must be limited to real date-bearing hashes."""
    policy = _load_yaml(POLICY_PATH)
    hash_policy = cast(dict[str, object], policy["content_hash_datetime_policy"])
    inventory = cast(
        list[dict[str, object]],
        hash_policy.get("date_only_entity_inventory", []),
    )

    assert inventory == []

    for item in inventory:
        provider = str(item["provider"])
        entity = str(item["entity"])
        config = _load_yaml(ROOT / "configs" / "entities" / provider / f"{entity}.yaml")
        hash_policy_block = cast(dict[str, object], config.get("hash_policy", {}))
        policy_config = cast(
            dict[str, object], hash_policy_block.get("hash_policy", {})
        )
        include_fields = cast(list[object], policy_config.get("include_fields", []))
        assert any(
            isinstance(field, str) and DATE_FIELD_RE.search(field)
            for field in include_fields
        ), (
            f"{provider}.{entity} must not stay in the residual v1_date inventory "
            "unless its content hash includes explicit date-like fields"
        )
