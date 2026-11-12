"""The manifest builder preserves its explicitly injected ledger boundary."""

from __future__ import annotations

from unittest.mock import Mock, sentinel
import pytest
from bioetl.composition.runtime_builders import (
    _run_manifest_creation_support as subject,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("ledger", [None, sentinel.ledger])
def test_manifest_ledger_creation_preserves_inputs_and_optional_result(
    monkeypatch, ledger
):
    create = Mock(return_value=ledger)
    monkeypatch.setattr(subject, "_create_ledger_service", create)
    assert subject.create_ledger_service(sentinel.inputs, sentinel.context) is ledger
    create.assert_called_once_with(sentinel.inputs, sentinel.context)
