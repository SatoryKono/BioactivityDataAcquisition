"""Contract tests for the Actions health command."""

import sys
from unittest.mock import patch

from scripts.engineering.ops import check_actions_health


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
