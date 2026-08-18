"""Unit coverage for CodeRabbit exact-cover leaf runner helpers."""

from __future__ import annotations

import json

import pytest

from pathlib import Path

from scripts.ops.coderabbit.run_leaves import (
    build_review_command,
    classify_output,
    extract_rate_limit_wait_seconds,
    has_review_completion,
    parse_backoff_schedule,
    parse_wait_time_to_seconds,
    selected_leaves,
)


pytestmark = [pytest.mark.unit]


def test_parse_backoff_schedule_uses_default_when_blank() -> None:
    assert parse_backoff_schedule("", default="1800,1800") == (1800.0, 1800.0)


def test_parse_backoff_schedule_rejects_non_positive() -> None:
    with pytest.raises(ValueError, match="positive"):
        parse_backoff_schedule("30,0", default="1800")


def test_parse_wait_time_to_seconds_accepts_coderabbit_tokens() -> None:
    assert parse_wait_time_to_seconds("30 minutes") == 1800
    assert parse_wait_time_to_seconds("1 hour") == 3600
    assert parse_wait_time_to_seconds("45s") == 45


def test_extract_rate_limit_wait_seconds_reads_metadata() -> None:
    payload = {
        "type": "error",
        "errorType": "rate_limit",
        "message": "Rate limit exceeded",
        "metadata": {"waitTime": "30 minutes"},
    }
    output = json.dumps(payload)
    assert extract_rate_limit_wait_seconds(output) == 1800


def test_classify_output_rate_limit_includes_wait() -> None:
    payload = {
        "type": "error",
        "errorType": "rate_limit",
        "metadata": {"waitTime": "30 minutes"},
    }
    status, reason = classify_output(1, json.dumps(payload))
    assert status == "rate_limit"
    assert "1800" in reason


def test_classify_output_requires_review_completed() -> None:
    output = json.dumps({"type": "status", "phase": "analyzing"})
    status, reason = classify_output(0, output)
    assert status == "missing_output"
    assert "review_completed" in reason


def test_classify_output_ignores_rate_limit_text_inside_completed_review() -> None:
    output = "\n".join(
        (
            json.dumps(
                {"type": "finding", "fileName": "network_rate_limit_helpers.py"}
            ),
            json.dumps(
                {
                    "type": "finding",
                    "codegenInstructions": "Rate limit exceeded for provider",
                }
            ),
            json.dumps(
                {
                    "type": "complete",
                    "status": "review_completed",
                    "findings": 2,
                    "reviewedFiles": ["network_rate_limit_helpers.py"],
                }
            ),
        )
    )
    assert classify_output(0, output) == ("ok", "")


def test_build_review_command_uses_committed_to_stay_under_file_cap() -> None:
    command = build_review_command("/usr/bin/coderabbit", Path("prompt.md"))
    assert command[0] == "/usr/bin/coderabbit"
    assert command[1:4] == ["review", "--committed", "--base"]
    assert "--agent" in command
    assert "-c" in command


def test_build_review_command_omits_context_files_near_cap() -> None:
    command = build_review_command(
        "/usr/bin/coderabbit", Path("prompt.md"), file_count=300
    )
    assert "--committed" in command
    assert "-c" not in command


def test_selected_leaves_preserves_cr_leaves_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CR_LEAVES", "leaf-b,leaf-a")
    monkeypatch.delenv("CR_WAVE", raising=False)
    matrix = {
        "leaves": [
            {"id": "leaf-a", "wave": "A"},
            {"id": "leaf-b", "wave": "A"},
        ]
    }
    assert [leaf["id"] for leaf in selected_leaves(matrix)] == ["leaf-b", "leaf-a"]


def test_classify_output_too_many_files() -> None:
    payload = {
        "type": "error",
        "errorType": "review",
        "code": "too_many_files",
        "message": "Review failed: Too many files!",
    }
    status, reason = classify_output(1, json.dumps(payload))
    assert status == "too_many_files"
    assert "300" in reason


def test_has_review_completion_detects_terminal_event() -> None:
    output = "\n".join(
        (
            json.dumps({"type": "status", "phase": "analyzing"}),
            json.dumps(
                {"type": "complete", "status": "review_completed", "findings": 0}
            ),
        )
    )
    assert has_review_completion(output) is True
    assert classify_output(0, output) == ("ok", "")
