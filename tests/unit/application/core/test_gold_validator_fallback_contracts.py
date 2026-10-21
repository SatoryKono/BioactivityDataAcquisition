"""Unsupported validators and empty fail-closed diagnostics never certify a write."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bioetl.application.core._batch_writer_gold_support import (
    _call_outcome_channel,
    _raise_fail_closed,
)
from bioetl.domain.exceptions import SchemaViolationError
from bioetl.domain.types import ValidationResult

pytestmark = pytest.mark.unit


def test_validator_without_an_outcome_method_cannot_fabricate_a_channel():
    assert _call_outcome_channel(object(), [{"entity_id": "row"}]) is None


def test_fail_closed_decision_without_reason_still_raises_a_canonical_error():
    writer = SimpleNamespace(_debug_export_service=None)
    validator = SimpleNamespace(validate=lambda records: ValidationResult(valid=True))
    with pytest.raises(SchemaViolationError) as caught:
        _raise_fail_closed(writer, [{"entity_id": "row"}], validator, ())
    assert caught.value.errors == ["gold outcome channel fail-closed"]
