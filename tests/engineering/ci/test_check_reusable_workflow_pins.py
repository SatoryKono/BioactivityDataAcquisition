import sys
from pathlib import Path

import pytest
import yaml

# Add script path to import
sys.path.insert(0, str(Path("scripts/engineering/ci").resolve()))
from check_reusable_workflow_pins import check_pins

pytestmark = pytest.mark.unit


@pytest.fixture
def temp_dir(tmp_path):
    return tmp_path


def create_yaml(path, data):
    with Path(path).open("w") as f:
        yaml.dump(data, f)


def test_verified_bump_passes(temp_dir):
    registry_path = temp_dir / "registry.yaml"
    workflow_path = temp_dir / "workflow.yaml"

    create_yaml(
        registry_path,
        {
            "pins": [
                {
                    "path": "actions/checkout",
                    "sha": "3d3c42e5aac5ba805825da76410c181273ba90b1",
                }
            ]
        },
    )

    create_yaml(
        workflow_path,
        {
            "jobs": {
                "test": {
                    "steps": [
                        {
                            "uses": "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
                        }
                    ]
                }
            }
        },
    )

    assert check_pins(str(registry_path), [str(workflow_path)])


def test_synthetic_retarget_fails(temp_dir):
    registry_path = temp_dir / "registry.yaml"
    workflow_path = temp_dir / "workflow.yaml"

    create_yaml(
        registry_path,
        {
            "pins": [
                {
                    "path": "actions/checkout",
                    "sha": "3d3c42e5aac5ba805825da76410c181273ba90b1",
                }
            ]
        },
    )

    create_yaml(
        workflow_path,
        {
            "jobs": {
                "test": {
                    "steps": [
                        {
                            "uses": "actions/checkout@0000000000000000000000000000000000000000"
                        }
                    ]
                }
            }
        },
    )

    assert not check_pins(str(registry_path), [str(workflow_path)])


def test_tag_ref_fails(temp_dir):
    registry_path = temp_dir / "registry.yaml"
    workflow_path = temp_dir / "workflow.yaml"

    create_yaml(
        registry_path,
        {
            "pins": [
                {
                    "path": "actions/checkout",
                    "sha": "3d3c42e5aac5ba805825da76410c181273ba90b1",
                }
            ]
        },
    )

    create_yaml(
        workflow_path, {"jobs": {"test": {"steps": [{"uses": "actions/checkout@v3"}]}}}
    )

    assert not check_pins(str(registry_path), [str(workflow_path)])


def test_simultaneous_substitution_retarget_risk(temp_dir):
    # This fixture represents the "hostile-PR negative fixture".
    # A PR can substitute both the registry AND the workflow AND the checker if they run from PR ref.
    # We prove that if all 3 are PR-controlled, check_pins passes with malicious data.
    # Therefore, PR-controlled pin-check is NOT a trust boundary.
    registry_path = temp_dir / "registry.yaml"
    workflow_path = temp_dir / "workflow.yaml"

    malicious_sha = "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
    create_yaml(
        registry_path, {"pins": [{"path": "hostile/action", "sha": malicious_sha}]}
    )

    create_yaml(
        workflow_path,
        {"jobs": {"test": {"steps": [{"uses": f"hostile/action@{malicious_sha}"}]}}},
    )

    assert check_pins(str(registry_path), [str(workflow_path)])
