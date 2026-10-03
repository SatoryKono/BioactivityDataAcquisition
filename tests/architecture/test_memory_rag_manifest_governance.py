# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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
    # Derived manifests are machine-local; the tracked root policy must ignore
    # the entire lane even in a fresh clone without generated memory payloads.
    result = subprocess.run(
        [
            "git",
            "check-ignore",
            "--no-index",
            "src/memory/derived/rag/manifests/probe.json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "src/memory/derived/rag/manifests/probe.json"
