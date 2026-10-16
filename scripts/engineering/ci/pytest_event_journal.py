import os
import json
import uuid
import subprocess
from datetime import datetime, timezone, UTC
import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--event-journal-dir",
        action="store",
        default=None,
        help="Directory to store event journal receipts",
    )


class EventJournalPlugin:
    def __init__(self, config, path):
        self.config = config
        self.path = path
        self.file = open(path, "w", encoding="utf-8")
        self.worker_id = os.environ.get("PYTEST_XDIST_WORKER", "master")

    def record(self, event_type, data):
        # Allowlist safe environment variables, absolutely no secrets
        safe_env = {
            k: v
            for k, v in os.environ.items()
            if k
            in {
                "GITHUB_RUN_ID",
                "GITHUB_RUN_ATTEMPT",
                "PYTEST_XDIST_WORKER",
                "EXPECTED_CHECKOUT_SHA",
            }
        }
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event": event_type,
            "worker_id": self.worker_id,
            "env": safe_env,
            **data,
        }
        self.file.write(json.dumps(record) + "\n")
        self.file.flush()

    def pytest_collection_modifyitems(self, session, config, items):
        _ = session
        _ = config
        for item in items:
            self.record("collected", {"nodeid": item.nodeid})

    def pytest_deselected(self, items):
        for item in items:
            self.record("deselected", {"nodeid": item.nodeid})

    def pytest_runtest_logreport(self, report):
        self.record(
            "outcome",
            {
                "nodeid": report.nodeid,
                "when": report.when,
                "outcome": report.outcome,
                "passed": report.passed,
                "failed": report.failed,
                "skipped": report.skipped,
                "duration": getattr(report, "duration", 0.0),
            },
        )

    def pytest_sessionfinish(self, session, exitstatus):
        _ = session
        self.record("session_finish", {"exitstatus": int(exitstatus)})
        self.file.close()


def pytest_configure(config):
    journal_dir = config.getoption("--event-journal-dir")
    if not journal_dir:
        return

    expected_sha = os.environ.get("EXPECTED_CHECKOUT_SHA")
    if expected_sha:
        try:
            actual_sha = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.STDOUT
            ).strip()
            if actual_sha != expected_sha:
                pytest.exit(
                    f"EventJournal SHA mismatch: actual {actual_sha} != expected {expected_sha}"
                )
        except Exception as e:
            pytest.exit(f"EventJournal failed to check git SHA: {e}")

    worker_id = os.environ.get("PYTEST_XDIST_WORKER", "master")
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
    run_id = os.environ.get("GITHUB_RUN_ID", "local")

    unique_id = uuid.uuid4().hex
    path = os.path.join(
        journal_dir, f"receipt_{run_id}_{attempt}_{worker_id}_{unique_id}.jsonl"
    )
    os.makedirs(journal_dir, exist_ok=True)

    plugin = EventJournalPlugin(config, path)
    config.pluginmanager.register(plugin, "event_journal_plugin")
