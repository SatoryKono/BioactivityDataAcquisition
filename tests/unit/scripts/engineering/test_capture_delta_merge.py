"""Capture contracts using synthetic producer output, never benchmark evidence."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

from scripts.engineering.performance import capture_delta_merge as capture

pytestmark = pytest.mark.unit
SHA = "a" * 40
RAW_TIME = (
    "\tElapsed (wall clock) time (h:mm:ss or m:ss): 1:02.34\n"
    "\tMaximum resident set size (kbytes): 12345\n"
    "\tExit status: 0\n"
)


@pytest.mark.parametrize(
    "outcome", ["complete", "failed", "skipped", "incomplete", "rows"]
)
def test_capture_preserves_raw_evidence_and_rejects_unsuccessful_producer(
    tmp_path, monkeypatch, outcome
):
    def producer(command, **kwargs):
        Path(command[command.index("-o") + 1]).write_text(RAW_TIME)
        kwargs["stdout"].write("synthetic pytest output\n")
        assert kwargs["env"]["LC_ALL"] == "C"
        if outcome != "skipped":
            directory = tmp_path / "N10" / "N10-fixture"
            directory.mkdir()
            (directory / "merge_scaling_N10.json").write_text(
                json.dumps(
                    {
                        "status": "incomplete"
                        if outcome == "incomplete"
                        else "complete",
                        "n_merges_target": 10,
                        "n_merges_completed": 10,
                        "merges": [{"merge_time_raw_s": 0.25}] * 10,
                        "actual_final_rows": 4100,
                        "expected_final_rows": 4200 if outcome == "rows" else 4100,
                        "total_records_processed": 5000,
                    }
                )
            )
        return subprocess.CompletedProcess(command, 1 if outcome == "failed" else 0)

    monkeypatch.setattr(capture.subprocess, "run", producer)
    row = capture._capture(10, tmp_path, SHA)
    assert row["status"] == ("complete" if outcome == "complete" else "failed")
    assert row["source_revision"] == SHA
    assert (tmp_path / "N10/time.txt").read_text() == RAW_TIME
    assert (
        row["artifacts_sha256"]["N10/time.txt"]
        == hashlib.sha256(RAW_TIME.encode()).hexdigest()
    )
    markdown = capture.render_markdown({"source_revision": SHA, "runs": [row]})
    if outcome == "complete":
        assert row["wall_time"] == "1:02.34"
        assert row["peak_rss_kb"] == 12345
        assert row["merge_time_sum_s"] == 2.5
        assert "| 4100 | 5000 |" in markdown
    else:
        assert "error" in row
        assert "N=10 failed" in markdown
        assert "| 4100 | 5000 |" not in markdown


@pytest.mark.parametrize("raw", ["", "Maximum resident set size (kbytes): 123\n"])
def test_missing_time_metrics_are_not_invented(raw):
    with pytest.raises(ValueError, match="missing wall time or peak RSS"):
        capture._time_metrics(raw)


def test_capture_rejects_untracked_files_hidden_by_git_config(tmp_path, monkeypatch):
    for name in tuple(os.environ):
        if name.startswith("GIT_"):
            monkeypatch.delenv(name)
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "--quiet",
            "--allow-empty",
            "-m",
            "fixture",
        ],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(
        ["git", "config", "status.showUntrackedFiles", "no"],
        cwd=tmp_path,
        check=True,
    )
    untracked = tmp_path / "nested" / "source.py"
    untracked.parent.mkdir()
    untracked.write_text("# untracked source\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    output = tmp_path / "evidence"

    with pytest.raises(SystemExit) as exc:
        capture.main(["--output-dir", str(output)])

    assert exc.value.code == 2
    assert not output.exists()


@pytest.mark.parametrize("dirty,github_sha", [(True, SHA), (False, "b" * 40)])
def test_capture_rejects_unbound_source_before_creating_evidence(
    tmp_path, monkeypatch, dirty, github_sha
):
    monkeypatch.setattr(
        capture,
        "_git",
        lambda *args: (
            SHA if args[0] == "rev-parse" else (" M code.py" if dirty else "")
        ),
    )
    monkeypatch.setenv("GITHUB_SHA", github_sha)
    output = tmp_path / "evidence"
    with pytest.raises(SystemExit) as exc:
        capture.main(["--output-dir", str(output)])
    assert exc.value.code == 2
    assert not output.exists()
