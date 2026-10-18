"""Finalization, invocation, worker collection and identity contracts."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest
from scripts.engineering.ci.pytest_event_journal import reconcile_pass, verify_directory

_SPEC = importlib.util.spec_from_file_location(
    "journal_protocol_helpers", Path(__file__).with_name("test_event_journal.py")
)
assert _SPEC is not None and _SPEC.loader is not None
_HELPERS = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_HELPERS)
_identity = _HELPERS._identity
_start = _HELPERS._start
_collected = _HELPERS._collected
_phases = _HELPERS._phases
_finalized = _HELPERS._finalized
_write_receipt = _HELPERS._write_receipt
_load = _HELPERS._load
pytestmark = pytest.mark.architecture


@pytest.fixture
def secret_journal_identity(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    secret = "identity-secret-fixture-value"
    monkeypatch.setenv("TEST_API_TOKEN", secret)
    identity = _identity(role="controller", worker_id="controller")
    for field in identity:
        if field != "role":
            identity[field] = f"prefix-{secret}-suffix"
    identity["matrix"] = {"nested": [secret], "password": "matrix-password-fixture"}
    return identity


def test_identity_is_redacted_at_the_journal_write_boundary(
    tmp_path: Path, secret_journal_identity: dict[str, Any]
) -> None:
    from scripts.engineering.ci.pytest_event_journal import EventJournalPlugin

    path = tmp_path / "receipt.jsonl"
    plugin = EventJournalPlugin(None, path, secret_journal_identity)
    plugin.record("session_start", {})
    plugin.finalize()
    raw = path.read_text(encoding="utf-8")
    assert "identity-secret-fixture-value" not in raw
    assert "matrix-password-fixture" not in raw
    identity = json.loads(raw.splitlines()[0])["identity"]
    assert identity["role"] == "controller"
    assert "[redacted:" in identity["invocation_id"]
    assert secret_journal_identity["invocation_id"].endswith("-suffix")


@pytest.mark.parametrize(
    ("env_name", "value", "secret"),
    [
        ("BIOETL_JOURNAL_PASS", "password=swordfish", "swordfish"),
        ("BIOETL_JOURNAL_INVOCATION_ID", "token=topsecretvalue", "topsecretvalue"),
    ],
)
def test_environment_identity_assignments_are_not_written_as_plaintext(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    env_name: str,
    value: str,
    secret: str,
) -> None:
    from scripts.engineering.ci.pytest_event_journal import (
        EventJournalPlugin,
        _identity_from_env,
        _secret_values,
    )

    monkeypatch.setenv(env_name, value)
    identity = _identity_from_env(actual_sha=None, secrets=_secret_values())
    path = tmp_path / "receipt.jsonl"
    plugin = EventJournalPlugin(None, path, identity)
    plugin.record("session_start", {})
    plugin.finalize()
    assert secret not in path.read_text(encoding="utf-8")


def test_identity_env_strings_are_redacted(monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts.engineering.ci.pytest_event_journal import (
        _identity_from_env,
        _safe_env,
        _secret_values,
    )

    monkeypatch.setenv("BIOETL_JOURNAL_PASS", "password=swordfish")
    monkeypatch.setenv("BIOETL_JOURNAL_INVOCATION_ID", "token=topsecretvalue")
    monkeypatch.setenv("PYTEST_XDIST_WORKER", "gw0")
    secrets = _secret_values()
    identity = _identity_from_env(actual_sha="a" * 40, secrets=secrets)
    blob = json.dumps(identity, sort_keys=True)
    assert "swordfish" not in blob
    assert "topsecretvalue" not in blob
    assert "[redacted:" in str(identity["pass_name"])
    assert "[redacted:" in str(identity["invocation_id"])
    assert identity["worker_id"] == "gw0"
    assert identity["role"] == "worker"
    safe = json.dumps(_safe_env(secrets), sort_keys=True)
    assert "swordfish" not in safe
    assert "topsecretvalue" not in safe


def _complete(directory: Path, pass_name: str = "parallel") -> Path:
    identity = _identity(role="controller", worker_id="controller", pass_name=pass_name)
    events = [
        _start(identity),
        _collected(identity, ["a"]),
        *_phases(identity, "a", "passed"),
        {"event": "session_finish", "identity": identity, "exitstatus": 0},
        {"event": "cmdline_finish", "identity": identity, "exitstatus": 0},
    ]
    _write_receipt(
        directory, _finalized(events), name="receipt_" + pass_name + ".jsonl"
    )
    return directory / ("receipt_" + pass_name + ".jsonl")


def test_new_missing_cmdline_finish_is_unknown(tmp_path: Path) -> None:
    path = _complete(tmp_path)
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows = [row for row in rows if row["event"] != "cmdline_finish"]
    rows[-1]["prior_line_count"] = len(rows) - 1
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    assert verify_directory(tmp_path, executed_passes=["parallel"]) == 4


def test_new_saved_passes_cannot_drop_pinned_invocation(tmp_path: Path) -> None:
    from scripts.engineering.ci.pytest_event_journal import reconcile_directory

    _complete(tmp_path)
    path = _complete(tmp_path, "serial")
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    path.write_text("".join(json.dumps(row) + "\n" for row in rows[:-1]))
    stored = reconcile_directory(tmp_path, executed_passes=["parallel", "serial"])
    stored["executed_passes"] = ["parallel"]
    (tmp_path / "journal-verdict.json").write_text(json.dumps(stored))
    assert verify_directory(tmp_path) == 4


def test_new_matrix_keys_are_redacted(monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts.engineering.ci.pytest_event_journal import _redacted_matrix, _safe_env

    fixture = "synthetic-matrix-fixture-only"
    raw = json.dumps({"token=" + fixture: "x", "password": {"token=" + fixture: "y"}})
    monkeypatch.setenv("BIOETL_JOURNAL_MATRIX", raw)
    leaked = fixture in json.dumps([_redacted_matrix(raw, ()), _safe_env(())])
    assert leaked is False


def test_new_each_worker_must_supply_collection(tmp_path: Path) -> None:
    controller = _identity(role="controller", worker_id="controller")
    a = _identity(role="worker", worker_id="gw0")
    b = _identity(role="worker", worker_id="gw1")
    events = [
        _start(controller),
        _start(a),
        _start(b),
        _collected(a, ["a", "b"]),
        *_phases(a, "a", "passed"),
        *_phases(b, "b", "passed"),
        {"event": "session_finish", "identity": controller, "exitstatus": 0},
        {"event": "cmdline_finish", "identity": controller, "exitstatus": 0},
    ]
    _write_receipt(tmp_path, _finalized(events))
    assert reconcile_pass(_load(tmp_path), pass_name="parallel")["status"] != "complete"
