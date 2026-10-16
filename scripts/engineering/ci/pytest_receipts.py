"""Pytest plugin for immutable per-worker/per-attempt receipts."""

import os
import json
import uuid
import subprocess
from pathlib import Path

ALLOWED_ENV_VARS = {
    "CI",
    "GITHUB_ACTIONS",
    "PYTEST_XDIST_WORKER",
    "GITHUB_RUN_ID",
    "GITHUB_RUN_ATTEMPT",
}


def get_git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except subprocess.CalledProcessError:
        return "unknown"


def pytest_addoption(parser):
    parser.addoption(
        "--receipt-dir", action="store", default=None, help="Directory for receipts"
    )
    parser.addoption("--receipt-run-id", action="store", default="local", help="Run ID")
    parser.addoption(
        "--receipt-attempt", action="store", default="1", help="Attempt ID"
    )
    parser.addoption(
        "--receipt-expected-sha",
        action="store",
        default=None,
        help="Expected checkout SHA",
    )


class ReceiptPlugin:
    def __init__(self, receipt_dir, run_id, attempt, expected_sha):
        self.receipt_dir = Path(receipt_dir)
        self.run_id = run_id
        self.attempt = attempt
        self.expected_sha = expected_sha
        self.worker_id = os.environ.get("PYTEST_XDIST_WORKER", "master")
        self.selected = 0
        self.deselected = 0
        self.results = {}
        self.actual_sha = get_git_sha()

        if self.expected_sha and self.actual_sha != self.expected_sha:
            raise RuntimeError(
                f"Checkout SHA mismatch! Expected {self.expected_sha}, got {self.actual_sha}"
            )

    def pytest_collection_modifyitems(self, config, items):  # noqa: ARG002
        self.selected = len(items)

    def pytest_deselected(self, items):
        self.deselected += len(items)

    def pytest_runtest_logreport(self, report):
        if report.when == "setup" and report.outcome == "skipped":
            self._record_outcome(report.nodeid, "skipped")
        elif report.when == "setup" and report.outcome == "failed":
            self._record_outcome(report.nodeid, "error")
        elif report.when == "call":
            self._record_outcome(report.nodeid, report.outcome)

    def _record_outcome(self, nodeid, outcome):
        if nodeid not in self.results:
            self.results[nodeid] = []
        self.results[nodeid].append(outcome)

    def pytest_sessionfinish(self, session, exitstatus):  # noqa: ARG002
        # Handle cases where exitstatus is an Enum in pytest
        exit_code = int(exitstatus)
        receipt = {
            "run_id": self.run_id,
            "attempt": self.attempt,
            "worker": self.worker_id,
            "sha": self.actual_sha,
            "exit_code": exit_code,
            "collection": {"selected": self.selected, "deselected": self.deselected},
            "results": self.results,
            "environment": {
                k: v for k, v in os.environ.items() if k in ALLOWED_ENV_VARS
            },
        }

        file_name = f"receipt_{uuid.uuid4().hex}.json"
        target_dir = self.receipt_dir / self.run_id / self.attempt / self.worker_id
        target_dir.mkdir(parents=True, exist_ok=True)
        # Atomic write
        temp_path = target_dir / (file_name + ".tmp")
        final_path = target_dir / file_name
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(receipt, f, indent=2)
        temp_path.replace(final_path)


def pytest_configure(config):
    receipt_dir = config.getoption("--receipt-dir")
    if receipt_dir:
        run_id = config.getoption("--receipt-run-id")
        attempt = config.getoption("--receipt-attempt")
        expected_sha = config.getoption("--receipt-expected-sha")
        config.pluginmanager.register(
            ReceiptPlugin(receipt_dir, run_id, attempt, expected_sha), "receipt_plugin"
        )
