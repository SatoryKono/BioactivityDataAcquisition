"""Registry coordinate coverage for governed ChEMBL enum catalog entries."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from bioetl.domain.schemas.constants import CHEMBL_ENUM_CATALOG
from scripts.docs.matrix.generate_pipeline_normalization_matrix import (
    ENUM_REGISTRY_PATHS,
    ENUM_REGISTRY_UNIONS,
)
from tests.integration.config.test_chembl_enum_parity import EXACT_DQ_ENUM_POLICIES

pytestmark = pytest.mark.integration

ROOT = Path(".")
ENUM_PATH = ROOT / "configs" / "enums" / "chembl.yaml"


@pytest.fixture(scope="module")
def chembl_enums() -> dict[str, Any]:
    loaded = yaml.safe_load(ENUM_PATH.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _registry_values(
    enums: dict[str, Any],
    registry_path: tuple[str, ...],
) -> frozenset[str]:
    union_paths = ENUM_REGISTRY_UNIONS.get(("configs/enums/chembl.yaml", registry_path))
    if union_paths is not None:
        return frozenset().union(
            *(_registry_values(enums, union_path) for union_path in union_paths)
        )
    current: Any = enums
    for part in registry_path:
        current = current[part]
    assert isinstance(current, list)
    return frozenset(str(value) for value in current)


def test_chembl_enum_catalog_keys_declare_matrix_registry_coordinates() -> None:
    missing = [
        f"chembl.{entity}.{field}"
        for entity, field in sorted(CHEMBL_ENUM_CATALOG)
        if ("chembl", entity, field) not in ENUM_REGISTRY_PATHS
    ]
    assert not missing, (
        "CHEMBL_ENUM_CATALOG entries missing ENUM_REGISTRY_PATHS coordinates:\n"
        + "\n".join(missing)
    )


@pytest.mark.parametrize(
    ("entity", "field"),
    sorted(CHEMBL_ENUM_CATALOG),
)
def test_chembl_enum_catalog_values_match_yaml_registry(
    chembl_enums: dict[str, Any],
    entity: str,
    field: str,
) -> None:
    registry_path = ENUM_REGISTRY_PATHS[("chembl", entity, field)]
    catalog_values = CHEMBL_ENUM_CATALOG[(entity, field)]
    yaml_values = _registry_values(chembl_enums, registry_path)
    assert catalog_values == yaml_values, (
        f"chembl.{entity}.{field} catalog drift: "
        f"missing={sorted(yaml_values - catalog_values)} "
        f"extra={sorted(catalog_values - yaml_values)}"
    )


def test_strict_dq_enum_fields_have_catalog_and_registry_coordinates() -> None:
    missing_catalog: list[str] = []
    missing_registry: list[str] = []

    for policy in EXACT_DQ_ENUM_POLICIES:
        coordinate = (policy.entity, policy.field)
        if coordinate not in CHEMBL_ENUM_CATALOG:
            missing_catalog.append(policy.label)
        if ("chembl", policy.entity, policy.field) not in ENUM_REGISTRY_PATHS:
            missing_registry.append(policy.label)

    assert not missing_catalog, (
        "Strict DQ enum fields missing CHEMBL_ENUM_CATALOG entries:\n"
        + "\n".join(missing_catalog)
    )
    assert not missing_registry, (
        "Strict DQ enum fields missing ENUM_REGISTRY_PATHS coordinates:\n"
        + "\n".join(missing_registry)
    )
