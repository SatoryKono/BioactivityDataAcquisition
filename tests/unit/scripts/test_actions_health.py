"""Contract tests for the Actions health command."""

from __future__ import annotations

import subprocess
import sys
from unittest.mock import patch

import pytest

from scripts.engineering.ops import check_actions_health

pytestmark = pytest.mark.unit


def test_reports_all_failed_zero_step_runs(capsys):
    runs = [
        {"id": number, "created_at": "2026-10-03T12:00:00Z"} for number in range(1, 15)
    ]

    def pages(endpoint):
        if "/jobs?" in endpoint:
            return [{"jobs": [{"conclusion": "failure", "steps": []}]}]
        return [{"total_count": len(runs), "workflow_runs": runs}]

    with (
        patch.object(
            sys,
            "argv",
            [
                "health",
                "--repo",
                "o/r",
                "--since",
                "2026-10-03",
                "--until",
                "2026-10-05",
            ],
        ),
        patch.object(check_actions_health, "api_pages", side_effect=pages),
    ):
        assert check_actions_health.main() == 1
    assert capsys.readouterr().out.strip().endswith(", ".join(map(str, range(1, 15))))


def test_daily_scan_detects_job_finishing_after_previous_scan(capsys):
    from datetime import UTC, datetime

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 5, 3, 5, tzinfo=tz or UTC)

    def pages(endpoint):
        if "/jobs?" in endpoint:
            assert "filter=latest" in endpoint
            return [
                {
                    "jobs": [
                        {
                            "conclusion": "failure",
                            "steps": [],
                            "completed_at": "2026-10-04T03:02:00Z",
                        }
                    ]
                }
            ]
        from urllib.parse import parse_qs, urlsplit

        created = parse_qs(urlsplit(endpoint).query)["created"][0]
        assert created.startswith("2026-10-02T03:05:00+00:00")
        return [
            {
                "total_count": 1,
                "workflow_runs": [{"id": 42, "created_at": "2026-10-03T04:00:00Z"}],
            }
        ]

    with (
        patch.object(sys, "argv", ["health", "--repo", "o/r"]),
        patch.object(check_actions_health, "datetime", FrozenDateTime),
        patch.object(check_actions_health, "api_pages", side_effect=pages),
    ):
        assert check_actions_health.main() == 1
    assert "42" in capsys.readouterr().out


def test_empty_selection_is_healthy(capsys):
    with (
        patch.object(sys, "argv", ["health", "--repo", "o/r"]),
        patch.object(
            check_actions_health,
            "api_pages",
            return_value=[{"total_count": 0, "workflow_runs": []}],
        ),
    ):
        assert check_actions_health.main() == 0
    assert "No failed zero-step jobs" in capsys.readouterr().out


def test_jobs_with_steps_or_success_are_healthy(capsys):
    def pages(endpoint):
        if "/jobs?" in endpoint:
            return [
                {
                    "jobs": [
                        {"conclusion": "success", "steps": []},
                        {"conclusion": "failure", "steps": [{"name": "test"}]},
                    ]
                }
            ]
        return [
            {
                "total_count": 1,
                "workflow_runs": [{"id": 42, "created_at": "2026-10-03T12:00:00Z"}],
            }
        ]

    with (
        patch.object(
            sys,
            "argv",
            [
                "health",
                "--repo",
                "o/r",
                "--since",
                "2026-10-03",
                "--until",
                "2026-10-05",
            ],
        ),
        patch.object(check_actions_health, "api_pages", side_effect=pages),
    ):
        assert check_actions_health.main() == 0
    assert "No failed zero-step jobs" in capsys.readouterr().out


def test_api_error_returns_error_status(capsys):
    error = subprocess.CalledProcessError(1, "gh", stderr="API unavailable")
    with (
        patch.object(sys, "argv", ["health", "--repo", "o/r"]),
        patch.object(check_actions_health, "api_pages", side_effect=error),
    ):
        assert check_actions_health.main() == 2
    assert "API unavailable" in capsys.readouterr().err
