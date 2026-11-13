"""Shipped adaptive bundles must retain their verifiable compiler inputs."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture
ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "grafana/plugins/bioetl-selectorshell-panel"


def test_adaptive_bundle_inputs_are_present_tracked_and_match_receipt() -> None:
    """Prevent shipping a bundle whose original build cannot be reconstructed."""
    receipt = json.loads((PLUGIN / "dist-adaptive/build-provenance.json").read_text())
    tracked = set(
        subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
        .decode()
        .split("\0")
    )
    problems = []
    for relative, expected in receipt["inputs_sha256_lf"].items():
        source = ROOT / relative
        if not source.is_file():
            problems.append(f"missing: {relative}")
            continue
        if relative not in tracked:
            problems.append(f"untracked: {relative}")
        normalized = source.read_bytes().replace(b"\r\n", b"\n")
        if hashlib.sha256(normalized).hexdigest() != expected:
            problems.append(f"receipt mismatch: {relative}")
    assert not problems, "\n".join(problems)
