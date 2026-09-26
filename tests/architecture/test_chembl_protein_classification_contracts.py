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
"""Architecture guards for ChEMBL protein-classification ownership."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
import yaml

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]


def _load_yaml(path: str) -> dict[str, Any]:
    with (ROOT / path).open(encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    assert isinstance(loaded, dict)
    return cast(dict[str, Any], loaded)


def _hash_include_fields(config_path: str) -> set[str]:
    config = _load_yaml(config_path)
    root_policy = config["hash_policy"]
    hash_policy = root_policy["hash_policy"]
    include_fields = hash_policy["include_fields"]
    assert isinstance(include_fields, list)
    return {str(field) for field in include_fields}


def test_chembl_target_hash_excludes_protein_classification_summary() -> None:
    include_fields = _hash_include_fields("configs/entities/chembl/target.yaml")

    forbidden_fields = {"protein_classifications"} | {
        f"target_protein_class_{part}_L{level}"
        for level in range(1, 6)
        for part in ("id", "name", "desc")
    }

    assert include_fields.isdisjoint(forbidden_fields)


def test_target_protein_classification_hash_includes_path_first_fields() -> None:
    include_fields = _hash_include_fields(
        "configs/entities/chembl/target_protein_classification.yaml"
    )

    assert {
        "path_ids",
        "path_names",
        "path_labels",
        "depth",
        "root_id",
        "is_leaf",
    }.issubset(include_fields)
