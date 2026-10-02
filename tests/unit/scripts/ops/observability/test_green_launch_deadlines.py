"""Process deadlines cover configured stages without changing acceptance gates."""

import yaml
from scripts.ops.observability.green_acceptance import Case, command, launch_timeout


def test_composite_deadline_covers_long_enricher(tmp_path):
    folder = tmp_path / "configs/composites"
    folder.mkdir(parents=True)
    (folder / "molecule.yaml").write_text(
        yaml.safe_dump(
            {
                "composite": {
                    "dependencies": [{"timeout_seconds": 300}],
                    "enrichers": [{"timeout_seconds": 7200}],
                }
            }
        )
    )
    assert launch_timeout(Case("composite", "composite_molecule"), tmp_path) == 9900


def test_workflow_deadline_covers_all_steps(tmp_path):
    folder = tmp_path / "configs/workflows"
    folder.mkdir(parents=True)
    (folder / "pack.yaml").write_text(
        yaml.safe_dump(
            {
                "workflow": {
                    "steps": [
                        {"kind": "pipeline"},
                        {"kind": "pipeline"},
                        {"kind": "transform"},
                    ]
                }
            }
        )
    )
    assert launch_timeout(Case("workflow", "pack"), tmp_path) == 4200


def test_pipeline_deadline_and_composite_health_server():
    assert launch_timeout(Case("pipeline", "chembl_target"), None) == 1800
    assert "--no-health-server" in command(Case("composite", "composite_target"))
