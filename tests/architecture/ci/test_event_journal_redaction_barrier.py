"""Journal write barrier when a raw secret survives redaction."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.architecture


def _identity() -> dict[str, Any]:
    return {
        "workflow_run_id": "run-1",
        "workflow_run_attempt": "1",
        "job": "serial-coverage",
        "matrix": None,
        "actual_checkout_sha": "a" * 40,
        "expected_checkout_sha": None,
        "invocation_id": "inv-1",
        "pass_name": "parallel",
        "worker_id": "controller",
        "role": "controller",
    }


def test_record_replaces_a_line_that_still_contains_a_secret(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.engineering.ci import pytest_event_journal as journal

    secret = "swordfish-secret"
    monkeypatch.setenv("BIOETL_UNIT_PASSWORD", secret)
    path = tmp_path / "receipt.jsonl"
    plugin = journal.EventJournalPlugin(None, path, _identity())
    monkeypatch.setattr(journal, "_redact_structured", lambda value, _secrets: value)
    plugin.record("session_start", {"password": secret})
    assert plugin._file is not None
    plugin._file.close()
    text = path.read_text(encoding="utf-8")
    assert secret not in text
    assert text == '{"event":"redaction_blocked","schema_version":1}\n'


def test_record_retains_event_when_secret_matches_redaction_label(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.engineering.ci import pytest_event_journal as journal

    secret = "redacted:"
    monkeypatch.setenv("BIOETL_UNIT_PASSWORD", secret)
    path = tmp_path / "receipt.jsonl"
    plugin = journal.EventJournalPlugin(None, path, _identity())
    plugin.record("session_start", {"password": secret})
    assert plugin._file is not None
    plugin._file.close()
    text = path.read_text(encoding="utf-8")
    assert secret not in text
    event = json.loads(text)
    assert event["event"] == "session_start"
    assert event["password"] != secret
