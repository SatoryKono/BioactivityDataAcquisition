from __future__ import annotations

import json
from pathlib import Path

from scripts.engineering.qa.reduce_architecture_debt import main


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
