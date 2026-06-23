"""Unit tests for deterministic test identity helpers."""

from __future__ import annotations

from uuid import UUID

import pytest

from bioetl.domain.types import BatchID, RunID
from tests.helpers import deterministic_ids

pytestmark = pytest.mark.unit


def test_typed_run_and_batch_helpers_return_expected_types() -> None:
    run_id = deterministic_ids.deterministic_run_uuid("helpers.run")
    batch_id = deterministic_ids.deterministic_batch_uuid("helpers.batch")

    assert isinstance(run_id, UUID)
    assert isinstance(batch_id, UUID)
    assert RunID(run_id) == run_id
    assert BatchID(batch_id) == batch_id


def test_string_helpers_roundtrip_to_typed_wrappers() -> None:
    run_id = deterministic_ids.deterministic_run_id("helpers.run")
    batch_id = deterministic_ids.deterministic_batch_id("helpers.batch")

    assert run_id == str(deterministic_ids.deterministic_run_uuid("helpers.run"))
    assert batch_id == str(deterministic_ids.deterministic_batch_uuid("helpers.batch"))


def test_callsite_helpers_are_stable_per_callsite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "PYTEST_CURRENT_TEST",
        "tests/unit/helpers/test_deterministic_ids.py::test_callsite_helpers_are_stable_per_callsite (call)",
    )

    def _capture() -> tuple[RunID, BatchID, str]:
        return (
            deterministic_ids.deterministic_run_uuid_from_callsite("helpers"),
            deterministic_ids.deterministic_batch_uuid_from_callsite("helpers"),
            deterministic_ids.deterministic_uuid_string_from_callsite("helpers"),
        )

    first = _capture()
    second = _capture()

    assert first != second
    assert isinstance(first[0], UUID)
    assert isinstance(first[1], UUID)
    assert UUID(first[2]) != UUID(second[2])
