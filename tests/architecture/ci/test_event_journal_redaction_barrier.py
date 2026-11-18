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


def test_line_for_storage_blocks_a_json_escaped_secret() -> None:
    from scripts.engineering.ci import pytest_event_journal as journal

    secret = 'quote"secret\nnext'
    line = json.dumps({"notes": secret}, ensure_ascii=True) + "\n"
    assert secret not in line
    stored = journal._line_for_storage(line, (secret,))
    assert stored == '{"event":"redaction_blocked","schema_version":1}\n'
    assert secret not in stored
    assert "quote" not in stored


def test_password_env_value_is_not_fingerprinted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.engineering.ci import pytest_event_journal as journal

    password = "swordfish-secret"
    monkeypatch.setenv("BIOETL_UNIT_PASSWORD", password)
    seen: list[str] = []
    original = journal._correlation_tag

    def spy(captured: str) -> str:
        seen.append(captured)
        return original(captured)

    monkeypatch.setattr(journal, "_correlation_tag", spy)
    path = tmp_path / "receipt.jsonl"
    plugin = journal.EventJournalPlugin(None, path, _identity())
    plugin.record("session_start", {"notes": f"prefix {password} suffix"})
    assert plugin._file is not None
    plugin._file.close()
    text = path.read_text(encoding="utf-8")
    assert password not in text
    assert password not in "".join(seen)
    payload = json.loads(text)
    assert payload["event"] == "session_start"
    assert payload["notes"] == "prefix [redacted] suffix"


def test_record_redacts_a_secret_nested_in_a_tuple(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.engineering.ci import pytest_event_journal as journal

    secret = 'quote"secret'
    monkeypatch.setenv("BIOETL_UNIT_TOKEN", secret)
    path = tmp_path / "receipt.jsonl"
    plugin = journal.EventJournalPlugin(None, path, _identity())
    plugin.record("session_start", {"notes": (secret,)})
    assert plugin._file is not None
    plugin._file.close()
    text = path.read_text(encoding="utf-8")
    payload = json.loads(text)
    assert payload["event"] == "session_start"
    assert re.fullmatch(r"\[redacted:[0-9a-f]{12}\]", payload["notes"][0])
    visible = re.sub(r"\[redacted:[0-9a-f]{12}\]", "", text)
    assert secret not in visible
    assert json.dumps(secret, ensure_ascii=True)[1:-1] not in visible


def _spy_correlation(monkeypatch: pytest.MonkeyPatch, journal: Any) -> list[str]:
    seen: list[str] = []
    original = journal._correlation_tag

    def spy(captured: str) -> str:
        seen.append(captured)
        return original(captured)

    monkeypatch.setattr(journal, "_correlation_tag", spy)
    return seen


def test_passphrase_env_value_is_sealed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.engineering.ci import pytest_event_journal as journal

    phrase = "phrase-canary-value"
    monkeypatch.setenv("BIOETL_UNIT_PASSPHRASE", phrase)
    seen = _spy_correlation(monkeypatch, journal)
    path = tmp_path / "receipt.jsonl"
    plugin = journal.EventJournalPlugin(None, path, _identity())
    plugin.record("session_start", {"notes": phrase})
    assert plugin._file is not None
    plugin._file.close()
    text = path.read_text(encoding="utf-8")
    assert phrase not in text
    assert phrase not in journal._keyed_env_needles()
    assert not any(phrase in item for item in seen)
    payload = json.loads(text)
    assert payload["event"] == "session_start"
    assert payload["notes"] == "[redacted]"


def test_password_stays_sealed_after_removal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.engineering.ci import pytest_event_journal as journal

    password = "ephemeral-canary-42"
    monkeypatch.setenv("BIOETL_UNIT_PASSWORD", password)
    seen = _spy_correlation(monkeypatch, journal)
    path = tmp_path / "receipt.jsonl"
    plugin = journal.EventJournalPlugin(None, path, _identity())
    plugin.record("session_start", {"notes": "collect"})
    monkeypatch.delenv("BIOETL_UNIT_PASSWORD")
    nodeid = f"test_file.py::test_value[{password}]"
    plugin.record("outcome", {"nodeid": nodeid})
    assert plugin._file is not None
    plugin._file.close()
    text = path.read_text(encoding="utf-8")
    assert password not in text
    assert not any(password in item for item in seen)
    lines = [json.loads(line) for line in text.splitlines() if line]
    assert [line["event"] for line in lines] == ["session_start", "outcome"]
    assert lines[1]["nodeid"] == "test_file.py::test_value[[redacted]]"


def test_password_rotation_seals_old_and_new_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.engineering.ci import pytest_event_journal as journal

    original = "rotation-canary-old-value"
    rotated = "rotation-canary-new-value"
    monkeypatch.setenv("BIOETL_UNIT_PASSWORD", original)
    seen = _spy_correlation(monkeypatch, journal)
    path = tmp_path / "receipt.jsonl"
    plugin = journal.EventJournalPlugin(None, path, _identity())
    plugin.record("session_start", {"notes": original})
    monkeypatch.setenv("BIOETL_UNIT_PASSWORD", rotated)
    plugin.record(
        "outcome", {"nodeid": f"test_file.py::test_value[{original}]", "notes": rotated}
    )
    assert plugin._file is not None
    plugin._file.close()
    text = path.read_text(encoding="utf-8")
    assert original not in text
    assert rotated not in text
    assert not any(original in item or rotated in item for item in seen)
    lines = [json.loads(line) for line in text.splitlines() if line]
    assert lines[0]["notes"] == "[redacted]"
    assert lines[1]["notes"] == "[redacted]"
    assert lines[1]["nodeid"] == "test_file.py::test_value[[redacted]]"


def test_spaced_env_token_does_not_leave_a_suffix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.engineering.ci import pytest_event_journal as journal

    token = "Bearer ExampleSensitiveToken123"
    suffix = "ExampleSensitiveToken123"
    monkeypatch.setenv("REVIEW_API_TOKEN", token)
    seen = _spy_correlation(monkeypatch, journal)
    path = tmp_path / "receipt.jsonl"
    plugin = journal.EventJournalPlugin(None, path, _identity())
    plugin.record("session_start", {"notes": f"authorization={token}"})
    assert plugin._file is not None
    plugin._file.close()
    text = path.read_text(encoding="utf-8")
    assert token not in text
    assert suffix not in text
    assert token in seen
    assert suffix not in seen
    payload = json.loads(text)
    assert payload["event"] == "session_start"
    assert suffix not in payload["notes"]


@pytest.mark.parametrize("escaped", [False, True])
def test_journal_seals_complete_keyed_value_containing_password(
    monkeypatch: pytest.MonkeyPatch, escaped: bool
) -> None:
    from scripts.engineering.ci import pytest_event_journal as journal

    password = "fixture-overlap-password"
    value = password + ' independent-fixture-tail"\nnext'
    monkeypatch.setenv("BIOETL_UNIT_PASSWORD", password)
    monkeypatch.setenv("BIOETL_UNIT_TOKEN", value)
    seen: list[str] = []
    original = journal._correlation_tag

    def spy(captured: str) -> str:
        seen.append(captured)
        return original(captured)

    monkeypatch.setattr(journal, "_correlation_tag", spy)
    text = json.dumps(value, ensure_ascii=True)[1:-1] if escaped else value
    stored = journal._line_for_storage(
        journal._redact_text("authorization=" + text, journal._secret_values()),
        journal._secret_values(),
    )
    assert stored == "authorization=[redacted]"
    assert "independent-fixture-tail" not in stored
    assert all(password not in captured for captured in seen)
