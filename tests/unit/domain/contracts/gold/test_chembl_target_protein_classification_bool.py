"""TPC gold nullable bools accept mixed None/True batches (#11213 / #11214)."""

from __future__ import annotations

import pytest

from bioetl.domain.contracts.gold._chembl_target_lookup_schemas import (
    ChEMBLTargetProteinClassificationGoldSchema,
)
from bioetl.infrastructure.validation.contract_validator import ContractAwareGoldValidator
from bioetl.infrastructure.validation.pandera_validator import PanderaGoldValidator

_HASH_A = "0" * 64
_HASH_B = "1" * 64
_SCHEMA_COLS = list(
    ChEMBLTargetProteinClassificationGoldSchema.to_schema().columns.keys()
)


def _tpc_gold_rows() -> list[dict[str, object]]:
    """Minimal gold rows with every schema column present (production projects them)."""
    base = {name: None for name in _SCHEMA_COLS}
    return [
        {
            **base,
            "_dq_warn": False,
            "_dq_error": False,
            "_index": 0,
            "entity_id": "CHEMBL1:missing_classification",
            "content_hash": _HASH_A,
            "target_id": "CHEMBL1",
            "classification_status": "missing_classification",
            "is_leaf": None,
            "l1_counts_for_target_type": False,
        },
        {
            **base,
            "_dq_warn": False,
            "_dq_error": False,
            "_index": 1,
            "entity_id": "CHEMBL2:1:2",
            "content_hash": _HASH_B,
            "target_id": "CHEMBL2",
            "classification_status": "resolved",
            "component_id": 1.0,
            "leaf_id": 2.0,
            "is_leaf": True,
            "l1_counts_for_target_type": True,
        },
    ]


@pytest.mark.unit
def test_tpc_gold_schema_nullable_is_leaf_none_true_batch():
    validator = PanderaGoldValidator(
        schema=ChEMBLTargetProteinClassificationGoldSchema,
        strict=True,
    )
    assert hasattr(validator._schema, "columns")
    result = validator.validate(_tpc_gold_rows())
    assert result.valid is True, result.errors


@pytest.mark.unit
def test_tpc_gold_contract_aware_nullable_is_leaf_none_true_batch():
    validator = ContractAwareGoldValidator(
        schema=ChEMBLTargetProteinClassificationGoldSchema,
        strict=True,
    )
    result = validator.validate(_tpc_gold_rows())
    assert result.valid is True, result.errors
