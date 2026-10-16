import os
import json
import subprocess


def test_event_journal_negative_secret_leak(tmp_path):
    journal_dir = tmp_path / "journal"
    test_file = tmp_path / "test_dummy.py"
    test_file.write_text("def test_ok(): pass\n")

    env = os.environ.copy()
    env["SUPER_SECRET_TOKEN"] = "do-not-leak-me"
    env["GITHUB_RUN_ID"] = "12345"

    subprocess.run(
        [
            "uv",
            "run",
            "python",
            "-m",
            "pytest",
            str(test_file),
            "-p",
            "scripts.engineering.ci.pytest_event_journal",
            f"--event-journal-dir={journal_dir}",
        ],
        env=env,
        capture_output=True,
        check=True,
    )

    receipts = list(journal_dir.glob("receipt_*.jsonl"))
    assert len(receipts) == 1

    for line in receipts[0].read_text().splitlines():
        data = json.loads(line)
        if "env" in data:
            assert "SUPER_SECRET_TOKEN" not in data["env"]
            assert data["env"].get("GITHUB_RUN_ID") == "12345"


def test_event_journal_sha_mismatch(tmp_path):
    journal_dir = tmp_path / "journal"
    test_file = tmp_path / "test_dummy.py"
    test_file.write_text("def test_ok(): pass\n")

    env = os.environ.copy()
    env["EXPECTED_CHECKOUT_SHA"] = "invalid-sha-123456"

    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "-m",
            "pytest",
            str(test_file),
            "-p",
            "scripts.engineering.ci.pytest_event_journal",
            f"--event-journal-dir={journal_dir}",
        ],
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert (
        "EventJournal SHA mismatch" in result.stderr
        or "EventJournal SHA mismatch" in result.stdout
    )


def test_event_journal_race_conditions(tmp_path):
    journal_dir = tmp_path / "journal"
    test_file = tmp_path / "test_dummy.py"
    test_file.write_text("def test_ok1(): pass\ndef test_ok2(): pass\n")

    env = os.environ.copy()

    subprocess.run(
        [
            "uv",
            "run",
            "python",
            "-m",
            "pytest",
            str(test_file),
            "-n",
            "2",
            "-p",
            "scripts.engineering.ci.pytest_event_journal",
            f"--event-journal-dir={journal_dir}",
        ],
        env=env,
        capture_output=True,
        check=True,
    )

    receipts = list(journal_dir.glob("receipt_*.jsonl"))
    # In xdist, there's master + 2 workers
    assert len(receipts) == 3

    events = []
    for receipt in receipts:
        for line in receipt.read_text().splitlines():
            events.append(json.loads(line))

    # Check that test_ok1 and test_ok2 appear
    nodeids = [
        e.get("nodeid")
        for e in events
        if e.get("event") == "outcome" and e.get("when") == "call"
    ]
    assert any("test_ok1" in node for node in nodeids)
    assert any("test_ok2" in node for node in nodeids)
