"""Tests for shared control-plane ledger identity helpers."""

from __future__ import annotations

import pytest

from bioetl.application.services.control_plane.ledger_identity_support import (
    build_ledger_idempotency_key,
)


@pytest.mark.unit
def test_build_ledger_idempotency_key_is_stable_for_selected_fields() -> None:
    fields = ("manifest_id", "run_id", "event_type")
    payload = {
        "manifest_id": "manifest-1",
        "run_id": "run-1",
        "event_type": "run_started",
        "ignored": "first",
    }

    first_key = build_ledger_idempotency_key(payload, fields=fields)
    second_key = build_ledger_idempotency_key(
        {**payload, "ignored": "second"},
        fields=fields,
    )

    assert first_key == second_key
    assert first_key.startswith("sha256:")


@pytest.mark.unit
def test_build_ledger_idempotency_key_changes_when_semantic_field_changes() -> None:
    fields = ("manifest_id", "run_id", "event_type")
    first_key = build_ledger_idempotency_key(
        {"manifest_id": "manifest-1", "run_id": "run-1", "event_type": "started"},
        fields=fields,
    )
    second_key = build_ledger_idempotency_key(
        {"manifest_id": "manifest-1", "run_id": "run-1", "event_type": "finished"},
        fields=fields,
    )

    assert first_key != second_key
