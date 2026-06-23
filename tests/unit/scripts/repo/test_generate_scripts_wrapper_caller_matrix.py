"""Unit tests for the scripts wrapper caller matrix generator."""

from __future__ import annotations

import pytest

from pathlib import Path

from scripts.engineering.repo import generate_scripts_wrapper_caller_matrix as module


pytestmark = pytest.mark.unit


def test_render_report_lists_known_wrapper_candidates(
    tmp_path: Path, monkeypatch
) -> None:
    # Mock file iteration to return minimal test files
    test_file = tmp_path / "docs" / "test.md"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("scripts/docs/build_docs_site.sh\n", encoding="utf-8")

    monkeypatch.setattr(
        module,
        "_iter_search_files",
        lambda root: [test_file],
    )

    report = module._render_report(tmp_path)

    assert "# Scripts CLI Wrapper Caller Matrix" in report
    assert "`scripts/docs/build_docs_site.sh`" in report
    assert "`scripts/engineering/repo/cleanup_branch_candidates.sh`" in report
    assert "`scripts/ops/launchers/codex/codex.sh`" in report
    assert "retain" in report
