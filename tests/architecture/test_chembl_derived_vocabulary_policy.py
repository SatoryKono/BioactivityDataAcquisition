"""Governance tests for raw/canonical ChEMBL derived-vocabulary policies."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.architecture._entity_contract_metadata_registry import (
    load_shared_quality_metadata,
)

pytestmark = [pytest.mark.architecture]


def _load_yaml(path: str) -> dict[str, Any]:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


@pytest.mark.parametrize(
    ("config_path", "policy_key", "scope", "raw_field", "canonical_field"),
    [
        (
            "configs/entities/chembl/assay_parameters.yaml",
            "assay_parameter_type_policy",
            "raw_plus_canonical_controlled_vocabulary",
            "type_raw",
            "type",
        ),
        (
            "configs/entities/chembl/subcellular_fraction.yaml",
            "subcellular_fraction_policy",
            "raw_plus_canonical_derived_vocabulary",
            "subcellular_fraction_raw",
            "subcellular_fraction",
        ),
    ],
)
def test_derived_vocabulary_policy_metadata_exists_and_documents_sidecars(
    config_path: str,
    policy_key: str,
    scope: str,
    raw_field: str,
    canonical_field: str,
) -> None:
    config = _load_yaml(config_path)
    metadata = load_shared_quality_metadata(config_path)

    assert policy_key in metadata
    policy = metadata[policy_key]
    assert policy.get("scope") == scope
    description = str(policy.get("description", ""))
    assert (
        "RAW-PLUS-CANONICAL" in description
        or "raw-plus-canonical" in description.lower()
    )

    field_semantics = policy.get("field_semantics", {})
    assert raw_field in field_semantics
    assert canonical_field in field_semantics
    assert any(
        term in str(field_semantics[raw_field]).lower()
        for term in ("raw", "source", "provider", "traceability", "review")
    )
    assert any(
        term in str(field_semantics[canonical_field]).lower()
        for term in ("canonical", "normalized", "silver", "gold", "downstream")
    )
