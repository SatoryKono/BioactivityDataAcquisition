from __future__ import annotations

import json
from pathlib import Path

import yaml

from scripts.engineering.qa.generate_architecture_debt_tasks import main

SAMPLE_DOMAIN_MODULE = "src/bioetl/domain/sample.py"


def test_generate_architecture_debt_tasks_script_writes_payload(tmp_path: Path) -> None:
    module_path = tmp_path / "src" / "bioetl" / "domain" / "sample.py"
    module_path.parent.mkdir(parents=True, exist_ok=True)
    module_path.write_text("def value() -> int:\n    return 1\n", encoding="utf-8")

    registry_path = tmp_path / "registry.yaml"
    registry_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "registries": {
                    "file_size_limits": {
                        SAMPLE_DOMAIN_MODULE: {
                            "value": 1,
                            "owner": "@bioetl-architecture",
                            "reason": "demo",
                            "expires_on": "2026-06-30",
                            "removal_step": "shrink file",
                        }
                    },
                    "function_complexity": {},
                    "function_length": {},
                    "class_size": {},
                    "class_method_count": {},
                    "god_object": {},
                    "domain_complexity": {},
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "tasks.json"

    rc = main(
        [
            "--registry",
            str(registry_path),
            "--project-root",
            str(tmp_path),
            "--output",
            str(output_path),
        ]
    )

    assert rc == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["registry_summary"]["total_tasks"] == 1
    assert payload["tasks"][0]["target_file"] == SAMPLE_DOMAIN_MODULE


def test_generate_architecture_debt_tasks_default_output_routes_to_reports_quality(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "src" / "bioetl" / "domain" / "sample.py"
    module_path.parent.mkdir(parents=True, exist_ok=True)
    module_path.write_text("def value() -> int:\n    return 1\n", encoding="utf-8")

    registry_path = tmp_path / "registry.yaml"
    registry_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "registries": {
                    "file_size_limits": {
                        SAMPLE_DOMAIN_MODULE: {
                            "value": 1,
                            "owner": "@bioetl-architecture",
                            "reason": "demo",
                            "expires_on": "2026-06-30",
                            "removal_step": "shrink file",
                        }
                    },
                    "function_complexity": {},
                    "function_length": {},
                    "class_size": {},
                    "class_method_count": {},
                    "god_object": {},
                    "domain_complexity": {},
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    rc = main(
        [
            "--registry",
            str(registry_path),
            "--project-root",
            str(tmp_path),
        ]
    )

    assert rc == 0
    output_files = list(
        (tmp_path / "reports" / "quality").glob(
            "tasks_architecture_metric_exemptions_*.json"
        )
    )
    assert len(output_files) == 1
    assert not list(tmp_path.glob("tasks_architecture_metric_exemptions_*.json"))
