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
from __future__ import annotations

import pytest

import json
from pathlib import Path

from scripts.engineering.qa.reduce_architecture_debt import main


pytestmark = pytest.mark.unit


def test_reduce_architecture_debt_script_writes_plan(tmp_path: Path) -> None:
    tasks_path = tmp_path / "tasks_architecture_metric_exemptions_2026-04-04-09-30.json"
    tasks_path.write_text(
        json.dumps(
            {
                "tasks": [
                    {
                        "id": "AME-001",
                        "registry": "file_size_limits",
                        "status": "within_limit",
                        "current_value": 200,
                        "delta_to_limit": -20,
                        "target_file": "src/bioetl/domain/sample.py",
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    output_path = tmp_path / "plan.json"

    rc = main(
        [
            "--tasks",
            str(tasks_path),
            "--project-root",
            str(tmp_path),
            "--output",
            str(output_path),
        ]
    )

    assert rc == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["summary"]["total_tasks"] == 1
    assert payload["batches"][0]["category"] == "STALE_EXEMPTION"


def test_reduce_architecture_debt_discovers_latest_tasks_under_reports_quality(
    tmp_path: Path,
) -> None:
    tasks_dir = tmp_path / "reports" / "quality"
    tasks_dir.mkdir(parents=True)
    older = tasks_dir / "tasks_architecture_metric_exemptions_2026-04-04-09-30.json"
    latest = tasks_dir / "tasks_architecture_metric_exemptions_2026-04-04-10-30.json"
    payload = {
        "tasks": [
            {
                "id": "AME-001",
                "registry": "file_size_limits",
                "status": "within_limit",
                "current_value": 200,
                "delta_to_limit": -20,
                "target_file": "src/bioetl/domain/sample.py",
            }
        ]
    }
    older.write_text(json.dumps({"tasks": []}) + "\n", encoding="utf-8")
    latest.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    output_path = tmp_path / "plan.json"

    rc = main(
        [
            "--project-root",
            str(tmp_path),
            "--output",
            str(output_path),
        ]
    )

    assert rc == 0
    plan = json.loads(output_path.read_text(encoding="utf-8"))
    assert plan["source_tasks_file"].endswith(latest.as_posix())
    assert plan["summary"]["total_tasks"] == 1
