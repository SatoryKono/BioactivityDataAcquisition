"""A target receipt cannot prove a commit for another table or contract."""

import pytest

from bioetl.domain.types.gold_contracts import GoldWriteCategory, GoldWriteReceipt
from bioetl.infrastructure.storage.gold.writer_implementation import (
    _validate_target_receipt,
)

pytestmark = pytest.mark.unit


def test_completed_receipt_cannot_prove_a_different_committed_target():
    receipt = GoldWriteReceipt("table", "1.0.0", GoldWriteCategory.COMPLETE, ("other",))
    with pytest.raises(TypeError, match="identity does not match"):
        _validate_target_receipt(receipt, "table", "1.0.0")


@pytest.mark.parametrize(
    "category", [GoldWriteCategory.NOT_COMMITTED, GoldWriteCategory.UNKNOWN]
)
def test_incomplete_target_receipt_is_not_promoted_to_success(category):
    from bioetl.domain.exceptions.gold_write import GoldWriteFailure

    receipt = GoldWriteReceipt("table", "1.0.0", category)
    with pytest.raises(GoldWriteFailure) as caught:
        _validate_target_receipt(receipt, "table", "1.0.0")
    assert caught.value.receipt is receipt


@pytest.mark.parametrize("receipt", [None, {}, True])
def test_untyped_target_result_is_rejected(receipt):
    with pytest.raises(TypeError, match="GoldWriteReceipt"):
        _validate_target_receipt(receipt, "target", "1")


@pytest.mark.parametrize("table, version", [("other", "1"), ("target", "other")])
def test_receipt_must_match_requested_identity(table, version):
    receipt = GoldWriteReceipt(table, version, GoldWriteCategory.COMPLETE, (table,))
    with pytest.raises(TypeError, match="identity does not match"):
        _validate_target_receipt(receipt, "target", "1")
