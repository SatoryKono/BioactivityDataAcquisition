"""Derived timeline artifacts must remain rebuild-only and untracked."""

from __future__ import annotations

import subprocess
from pathlib import Path

import yaml


def test_timeline_jsonl_is_untracked_and_policy_declares_rebuildable() -> None:
    completed = subprocess.run(
        ["git", "ls-files", "src/memory/derived/timeline/events/*.jsonl"],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.stdout.strip() == ""

    policy = yaml.safe_load(
        Path("src/memory/policy/retention.yaml").read_text(encoding="utf-8")
    )
    timeline = policy["artifact_classes"]["timeline_event"]
    assert timeline["rebuildable"] is True

    ignore = Path("src/memory/derived/timeline/events/.gitignore").read_text(
        encoding="utf-8"
    )
    assert "*" in ignore
    assert "!README.md" in ignore
