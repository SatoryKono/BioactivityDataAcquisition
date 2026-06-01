"""Tests for control-plane ledger idempotency key builders."""

from __future__ import annotations

import pytest

from bioetl.application.services.control_plane.ledger.entry_support import (
    build_run_ledger_idempotency_key,
)
from bioetl.application.services.control_plane.workflow.ledger_service import (
    _build_workflow_ledger_idempotency_key,
)


@pytest.mark.unit
def test_run_ledger_idempotency_key_is_stable_for_selected_fields() -> None:
    payload = {
        "manifest_id": "manifest-1",
        "run_id": "run-1",
        "event_type": "run_started",
        "ignored": "first",
    }

    first_key = build_run_ledger_idempotency_key(payload)
    second_key = build_run_ledger_idempotency_key(
        {**payload, "ignored": "second"},
    )

    assert first_key == second_key
    assert first_key.startswith("sha256:")


@pytest.mark.unit
def test_run_ledger_idempotency_key_changes_when_semantic_field_changes() -> None:
    first_key = build_run_ledger_idempotency_key(
        {"manifest_id": "manifest-1", "run_id": "run-1", "event_type": "started"}
    )
    second_key = build_run_ledger_idempotency_key(
        {"manifest_id": "manifest-1", "run_id": "run-1", "event_type": "finished"}
    )

    assert first_key != second_key


@pytest.mark.unit
def test_workflow_ledger_idempotency_key_is_stable_for_selected_fields() -> None:
    payload = {
        "manifest_id": "workflow-manifest-1",
        "workflow_run_id": "run-1",
        "event_type": "workflow_started",
        "ignored": "first",
    }

    first_key = _build_workflow_ledger_idempotency_key(payload)
    second_key = _build_workflow_ledger_idempotency_key(
        {**payload, "ignored": "second"}
    )

    assert first_key == second_key
    assert first_key.startswith("sha256:")
