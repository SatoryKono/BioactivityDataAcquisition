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
"""DQ/catalog sync gates for audited ChEMBL entity configs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts.docs.generate_pipeline_normalization_field_matrix import (
    build_field_matrix_rows,
)

ROOT = Path(".")
ENTITY_CONFIG_ROOT = ROOT / "configs" / "entities" / "chembl"
_AUDITED_ENTITIES = frozenset(
    {
        "activity",
        "assay",
        "assay_parameters",
        "cell_line",
        "molecule",
        "publication",
        "publication_term",
        "subcellular_fraction",
        "target",
        "target_component",
        "tissue",
    }
)


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    assert isinstance(payload, dict)
    return payload


def _matrix_lookup() -> dict[tuple[str, str], dict[str, str]]:
    return {
        (row["pipeline_name"], row["field_name"]): row
        for row in build_field_matrix_rows()
        if row["pipeline_name"].startswith("chembl_")
    }


@pytest.mark.integration
def test_audited_chembl_dq_enum_fields_are_synced_to_catalog_rows() -> None:
    matrix = _matrix_lookup()

    for entity in sorted(_AUDITED_ENTITIES):
        config = _load_yaml(ENTITY_CONFIG_ROOT / f"{entity}.yaml")
        validations = config.get("quality", {}).get("entity_field_validations", [])
        assert isinstance(validations, list)
        for validation in validations:
            if not isinstance(validation, dict) or validation.get("type") != "enum":
                continue
            field_name = str(validation["field"])
            row = matrix[(f"chembl_{entity}", field_name)]
            source_path = str(row["controlled_vocabulary_source"])

            assert row["dq_coverage"].startswith("enum:"), (
                f"Expected enum DQ coverage for chembl_{entity}.{field_name}, "
                f"got {row['dq_coverage']!r}"
            )
            assert source_path != "", (
                f"chembl_{entity}.{field_name} missing governed catalog source"
            )
            if source_path.startswith("configs/"):
                assert (ROOT / source_path).exists(), (
                    "Catalog source path does not exist for "
                    f"chembl_{entity}.{field_name}: {source_path}"
                )
            else:
                assert source_path.startswith(("domain.", "profile:")), (
                    f"chembl_{entity}.{field_name} uses unexpected catalog source "
                    f"{source_path!r}"
                )
            assert row["policy_scope"] != "", (
                f"Policy scope must be declared for chembl_{entity}.{field_name}"
            )
