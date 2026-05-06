"""Config alignment tests for ChEMBL activity content-hash policy."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from bioetl.infrastructure.config.pipeline_config_api import load_pipeline_config
from bioetl.domain.normalization.profiles import (
    CHEMBL_ACTIVITY_SCHEMA_FIELDS,
)

ACTIVITY_CONFIG_PATH = Path("configs/entities/chembl/activity.yaml")


def _load_activity_config() -> dict[str, Any]:
    with ACTIVITY_CONFIG_PATH.open(encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    assert isinstance(loaded, dict)
    return loaded


def _business_schema_fields(config: dict[str, Any]) -> frozenset[str]:
    column_groups = config["schema"]["column_groups"]
    business_group = next(
        group for group in column_groups if group.get("name") == "business"
    )
    return frozenset(business_group["fields"])


@pytest.mark.integration
def test_chembl_activity_hash_policy_uses_normalized_business_fields() -> None:
    """Root hash_policy should be the runtime-authoritative ChEMBL hash selector."""
    config = _load_activity_config()
    load_pipeline_config.cache_clear()
    loaded = load_pipeline_config("chembl_activity")

    assert loaded.content_hash.include == []
    assert loaded.content_hash.exclude == []
    assert loaded.content_hash_policy is not None

    include_fields = frozenset(loaded.content_hash_policy.include_fields)
    business_fields = _business_schema_fields(config)
    profile_fields = frozenset(CHEMBL_ACTIVITY_SCHEMA_FIELDS)

    assert include_fields <= business_fields
    assert include_fields <= profile_fields
    assert not include_fields & {
        "activity_chembl_id",
        "assay_chembl_id",
        "molecule_chembl_id",
        "confidence_score",
        "document_chembl_id",
        "year",
    }
