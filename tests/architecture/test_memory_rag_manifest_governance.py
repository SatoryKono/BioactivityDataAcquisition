"""Architecture guards for rebuild-only RAG manifest lifecycle."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture


def test_derived_rag_lane_tracks_only_policy_files() -> None:
    result = subprocess.run(
        ["git", "ls-files", "--", "src/memory/derived/rag/manifests"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    existing_tracked = {
        path for path in result.stdout.splitlines() if Path(path).is_file()
    }
    assert existing_tracked <= {
        "src/memory/derived/rag/manifests/.gitignore",
        "src/memory/derived/rag/manifests/README.md",
    }


def test_derived_rag_lane_ignores_generated_payloads() -> None:
    ignore_file = Path("src/memory/derived/rag/manifests/.gitignore")
    patterns = set(ignore_file.read_text(encoding="utf-8").splitlines())

    assert "*" in patterns
    assert "!.gitignore" in patterns
    assert "!README.md" in patterns
