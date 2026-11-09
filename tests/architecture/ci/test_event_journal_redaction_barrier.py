"""Journal write barrier when a raw secret survives redaction."""

from __future__ import annotations

import json
import re
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


def test_record_keeps_an_event_when_the_secret_is_inside_the_marker(
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
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["event"] == "session_start"
    assert re.fullmatch(r"\[redacted:[0-9a-f]{12}\]", payload["password"])
    visible = re.sub(r"\[redacted:[0-9a-f]{12}\]", "", json.dumps(payload))
    assert secret not in visible


def test_line_for_storage_still_blocks_a_raw_marker_prefix() -> None:
    from scripts.engineering.ci import pytest_event_journal as journal

    stored = journal._line_for_storage('{"password":"redacted:"}\n', ("redacted:",))
    assert stored == '{"event":"redaction_blocked","schema_version":1}\n'
