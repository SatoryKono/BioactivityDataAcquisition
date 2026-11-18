"""Journal write barrier when a raw secret survives redaction."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.architecture


@pytest.mark.parametrize("workers", [1, 2])
def test_live_xdist_late_password_keeps_controller_outcomes_selected(
    tmp_path: Path, workers: int
) -> None:
    from tests.architecture.ci.test_event_journal import _live_verdict, _run_journal

    config = tmp_path / "pytest.ini"
    config.write_text("[pytest]\n", encoding="utf-8")
    result = _run_journal(
        tmp_path,
        "import pytest\n"
        "@pytest.fixture(autouse=True)\n"
        "def discover(monkeypatch):\n"
        "    monkeypatch.setenv('REVIEW_PASSWORD', 'late-nodeid-password')\n"
        "@pytest.mark.parametrize('value', ['late-nodeid-password'])\n"
        "def test_first(value):\n"
        "    assert value\n"
        "@pytest.mark.parametrize('value', ['late-nodeid-password'])\n"
        "def test_second(value):\n"
        "    assert value\n",
        [
            "-c",
            str(config),
            "--basetemp",
            str(tmp_path / "temp"),
            "-p",
            "xdist.plugin",
            "-n",
            str(workers),
        ],
    )
    assert result.returncode == 0, result.stdout + result.stderr
    verdict = _live_verdict(tmp_path)
    assert verdict["status"] == "complete", verdict["reasons"]
    assert verdict["tests_passed"] is True
    assert len(verdict["passes"]["parallel"]["terminals"]) == 2
    assert "late-nodeid-password" not in json.dumps(verdict)


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


def test_password_overlap_seals_the_entire_known_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.engineering.ci import pytest_event_journal as journal

    password = "shared-password"
    token = password + " IndependentSensitiveToken123"
    monkeypatch.setenv("REVIEW_PASSWORD", password)
    monkeypatch.setenv("REVIEW_API_TOKEN", token)
    seen = _spy_correlation(monkeypatch, journal)
    path = tmp_path / "receipt.jsonl"
    plugin = journal.EventJournalPlugin(None, path, _identity())
    plugin.record("session_start", {"notes": f"authorization={token}"})
    plugin.finalize()
    text = path.read_text(encoding="utf-8")
    assert password not in text
    assert "IndependentSensitiveToken123" not in text
    assert not any(password in item for item in seen)
    assert json.loads(text.splitlines()[0])["notes"] == "authorization=[redacted]"


def test_journal_scans_password_environment_once_per_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.engineering.ci import pytest_event_journal as journal

    path = tmp_path / "receipt.jsonl"
    plugin = journal.EventJournalPlugin(None, path, _identity())
    original = journal._partition_env_needles
    scans: list[None] = []

    def spy() -> tuple[tuple[str, ...], tuple[str, ...]]:
        scans.append(None)
        return original()

    monkeypatch.setattr(journal, "_partition_env_needles", spy)
    plugin.record(
        "outcome", {"nested": [{"nodeid": "test.py::case", "notes": "ok"}] * 20}
    )
    assert len(scans) == 1
    scans.clear()
    monkeypatch.setenv("REVIEW_PASSWORD", "rotated-password-value")
    plugin.record("outcome", {"notes": "rotated-password-value"})
    assert len(scans) == 1
    plugin.finalize()
    assert "rotated-password-value" not in path.read_text(encoding="utf-8")


@pytest.mark.parametrize("discover_when", ["setup", "call"])
@pytest.mark.parametrize("copies", [1, 2])
@pytest.mark.parametrize("worker", [False, True])
def test_password_discovered_after_collection_keeps_terminal_matching(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    copies: int,
    worker: bool,
    discover_when: str,
) -> None:
    from scripts.engineering.ci import pytest_event_journal as journal

    password = "late-password-value"
    nodeid = f"test.py::test_case[{password}]"
    plugin = journal.EventJournalPlugin(
        None, tmp_path / "receipt_controller.jsonl", _identity()
    )
    writers = [plugin]
    if worker:
        identity = {**_identity(), "role": "worker", "worker_id": "gw0"}
        writers.append(
            journal.EventJournalPlugin(
                None, tmp_path / "receipt_worker.jsonl", identity
            )
        )
    for writer in writers:
        writer.record(
            "session_start",
            {
                "selection": {
                    "args": [],
                    "marker": "",
                    "collect_only": False,
                    "exitfirst": False,
                    "maxfail": 0,
                },
                "sha_error": None,
            },
        )
        writer.record("collection_finished", {"nodeids": [nodeid] * copies})
    for _ in range(copies):
        for when in ("setup", "call", "teardown"):
            if when == discover_when:
                monkeypatch.setenv("REVIEW_PASSWORD", password)
            for writer in writers:
                data = {
                    "nodeid": nodeid,
                    "when": when,
                    "classification": "passed",
                    "retry_index": 0,
                    "wasxfail": False,
                }
                if worker and writer is plugin:
                    data["origin_worker"] = "gw0"
                writer.record("outcome", data)
    for writer in writers:
        writer.record("session_finish", {"exitstatus": 0})
        if writer is plugin:
            writer.record("cmdline_finish", {"exitstatus": 0})
        writer.finalize()
    verdict = journal.reconcile_pass(
        journal._group_receipts(tmp_path), pass_name="parallel"
    )
    assert verdict["status"] == "complete", verdict["reasons"]
    assert verdict["tests_passed"] is True
    assert len(verdict["terminals"]) == copies
    assert password not in json.dumps(verdict)


@pytest.mark.parametrize("template", ["authorization={}", "ghp_{}"])
def test_unknown_credential_containing_password_is_sealed_in_full(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, template: str
) -> None:
    from scripts.engineering.ci import pytest_event_journal as journal

    password = "sharedpassword"
    monkeypatch.setenv("REVIEW_PASSWORD", password)
    seen = _spy_correlation(monkeypatch, journal)
    path = tmp_path / "receipt.jsonl"
    plugin = journal.EventJournalPlugin(None, path, _identity())
    plugin.record(
        "outcome", {"notes": template.format(password + "IndependentSensitive123")}
    )
    plugin.finalize()
    text = path.read_text(encoding="utf-8")
    assert password not in text
    assert "IndependentSensitive123" not in text
    assert not any(password in item for item in seen)


@pytest.mark.parametrize("keyword", ["password", "passphrase"])
@pytest.mark.parametrize("token", ["password", "passphrase"])
def test_token_cannot_hide_a_password_assignment_keyword(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, keyword: str, token: str
) -> None:
    from scripts.engineering.ci import pytest_event_journal as journal

    monkeypatch.setenv("BIOETL_UNIT_TOKEN", token)
    path = tmp_path / "receipt.jsonl"
    plugin = journal.EventJournalPlugin(None, path, _identity())
    plugin.record("outcome", {"notes": f"{keyword}=independent-canary-value"})
    plugin.finalize()
    assert "independent-canary-value" not in path.read_text(encoding="utf-8")


def test_inventory_fixture_reset_does_not_unseal_an_active_plugin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.engineering.ci import pytest_event_journal as journal

    password = "live-journal-password"
    monkeypatch.setenv("REVIEW_PASSWORD", password)
    path = tmp_path / "receipt.jsonl"
    plugin = journal.EventJournalPlugin(None, path, _identity())
    seen = _spy_correlation(monkeypatch, journal)
    monkeypatch.delenv("REVIEW_PASSWORD")
    journal._clear_retained_blocked()
    plugin.record("outcome", {"notes": password})
    plugin.finalize()
    assert password not in path.read_text(encoding="utf-8")
    assert not any(password in item for item in seen)


@pytest.mark.parametrize("field", ["password", "passphrase"])
def test_known_token_matching_a_password_field_does_not_hide_its_assignment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    from scripts.engineering.ci import pytest_event_journal as journal

    monkeypatch.setenv("BIOETL_UNIT_TOKEN", field)
    path = tmp_path / "receipt.jsonl"
    plugin = journal.EventJournalPlugin(None, path, _identity())
    seen = _spy_correlation(monkeypatch, journal)
    plugin.record("outcome", {"notes": f"{field}=independent-canary-value"})
    plugin.finalize()
    assert "independent-canary-value" not in path.read_text(encoding="utf-8")
    assert not any("independent-canary-value" in item for item in seen)


@pytest.mark.parametrize("encoded", [False, True])
def test_password_containing_a_keyed_secret_is_sealed_as_one_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, encoded: bool
) -> None:
    from scripts.engineering.ci import pytest_event_journal as journal

    token = "shared-token-value"
    password = 'IndependentSensitive123 "' + token + "\nnext"
    monkeypatch.setenv("REVIEW_PASSWORD", password)
    monkeypatch.setenv("REVIEW_API_TOKEN", token)
    seen = _spy_correlation(monkeypatch, journal)
    path = tmp_path / "receipt.jsonl"
    plugin = journal.EventJournalPlugin(None, path, _identity())
    value = json.dumps(password, ensure_ascii=True)[1:-1] if encoded else password
    plugin.record("outcome", {"nodeid": f"test.py::test_case[{value}]"})
    plugin.finalize()
    text = path.read_text(encoding="utf-8")
    assert "IndependentSensitive123" not in text
    assert not any(
        password in item or "IndependentSensitive123" in item for item in seen
    )
    assert (
        json.loads(text.splitlines()[0])["nodeid"] == "test.py::test_case[[redacted]]"
    )
