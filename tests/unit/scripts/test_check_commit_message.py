"""Unit tests for the local commit message validator."""

from __future__ import annotations

import pytest

from scripts.engineering.dev.check_commit_message import (
    MAX_CONVENTIONAL_HEADER_LENGTH,
    main,
    validate_commit_message_header,
)


pytestmark = pytest.mark.unit


def test_validate_commit_message_header_accepts_conventional_commit() -> None:
    assert (
        validate_commit_message_header("feat(hooks): install commit-msg hook") is None
    )


def test_validate_commit_message_header_accepts_merge_and_revert_headers() -> None:
    assert (
        validate_commit_message_header("Merge branch 'main' into feature/hooks") is None
    )
    assert (
        validate_commit_message_header('Revert "feat(hooks): install commit-msg hook"')
        is None
    )


def test_validate_commit_message_header_rejects_invalid_header() -> None:
    error = validate_commit_message_header("bad message")

    assert error is not None
    assert "Conventional Commits" in error


def test_validate_commit_message_header_rejects_overlong_conventional_header() -> None:
    header = "feat(hooks): " + ("x" * MAX_CONVENTIONAL_HEADER_LENGTH)

    error = validate_commit_message_header(header)

    assert error is not None
    assert "exceeds 100 characters" in error


def test_main_validates_commit_message_file(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    commit_msg = tmp_path / "COMMIT_EDITMSG"
    commit_msg.write_text(
        "feat(hooks): install commit-msg hook\n\nbody\n", encoding="utf-8"
    )

    exit_code = main([str(commit_msg)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""


def test_main_reports_invalid_commit_message_file(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    commit_msg = tmp_path / "COMMIT_EDITMSG"
    commit_msg.write_text("bad message\n", encoding="utf-8")

    exit_code = main([str(commit_msg)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Offending header" in captured.err
