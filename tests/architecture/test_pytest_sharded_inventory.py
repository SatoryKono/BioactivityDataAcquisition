"""Architecture guards for declarative pytest shard inventory."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = ROOT / "configs/quality/pytest_shards.yaml"
RUNNER_PATH = ROOT / "scripts/engineering/dev/run_pytest_sharded.sh"


def _bash_runner_path(path: Path) -> str:
    """Render a bash-friendly script path across Linux and Windows hosts."""
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        pass

    path_str = path.as_posix()
    if len(path_str) >= 3 and path_str[1:3] == ":/":
        return f"/{path_str[0].lower()}{path_str[2:]}"
    return path_str


def _load_inventory() -> dict[str, object]:
    return yaml.safe_load(INVENTORY_PATH.read_text(encoding="utf-8"))


@pytest.mark.architecture
def test_pytest_shard_inventory_declares_canonical_schema_and_aliases() -> None:
    inventory = _load_inventory()

    assert inventory["schema_version"] == 1
    assert inventory["source"] == "configs/quality/pytest_shards.yaml"

    shards = inventory["shards"]
    assert isinstance(shards, list)
    shard_names = [entry["name"] for entry in shards]
    assert shard_names == [
        "S1-domain-core",
        "S1-domain-services",
        "S2-comp-iface",
        "S7-crosscutting-architecture-a",
        "S7-crosscutting-architecture-a2",
        "S7-crosscutting-architecture-a3",
        "S3-app-foundation",
        "S4-app-services",
        "S7-crosscutting-architecture-b",
        "S5-infra-adapters",
        "S6-crosscutting-unit",
        "S7-crosscutting-architecture-c",
        "S7-crosscutting-architecture-guardrails",
        "S8-crosscutting-governance",
        "S7-crosscutting-architecture-d",
    ]

    aliases = inventory["aliases"]
    assert aliases["S7-crosscutting-architecture"]["expands_to"] == [
        "S7-crosscutting-architecture-a",
        "S7-crosscutting-architecture-a2",
        "S7-crosscutting-architecture-a3",
        "S7-crosscutting-architecture-b",
        "S7-crosscutting-architecture-c",
        "S7-crosscutting-architecture-d",
    ]
    assert aliases["S7-architecture-fast-boundary"]["expands_to"] == [
        "S7-crosscutting-architecture-a",
        "S7-crosscutting-architecture-a2",
        "S7-crosscutting-architecture-a3",
        "S7-crosscutting-architecture-b",
        "S7-crosscutting-architecture-c",
        "S7-crosscutting-architecture-d",
    ]
    assert aliases["S7-architecture-slow-governance"]["expands_to"] == [
        "S7-crosscutting-architecture-guardrails",
    ]


@pytest.mark.architecture
def test_sharded_runner_loads_declarative_inventory_and_documents_path() -> None:
    runner = RUNNER_PATH.read_text(encoding="utf-8")
    guide = (ROOT / "docs/03-guides/testing.md").read_text(encoding="utf-8")
    dev_readme = (ROOT / "scripts/engineering/dev/README.md").read_text(
        encoding="utf-8"
    )

    assert "configs/quality/pytest_shards.yaml" in runner
    assert "load_shard_inventory" in runner
    assert "configs/quality/pytest_shards.yaml" in guide
    assert "configs/quality/pytest_shards.yaml" in dev_readme


@pytest.mark.architecture
def test_sharded_runner_list_matches_inventory_order() -> None:
    inventory = _load_inventory()
    expected_names = [entry["name"] for entry in inventory["shards"]]

    result = subprocess.run(
        ["bash", _bash_runner_path(RUNNER_PATH), "--list"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    plan_lines = [
        line for line in result.stdout.splitlines() if re.match(r"^S\d-", line)
    ]
    actual_names = [line.split("  ", maxsplit=1)[0] for line in plan_lines]
    assert actual_names == expected_names


@pytest.mark.architecture
def test_sharded_runner_dry_run_expands_architecture_alias_from_inventory() -> None:
    result = subprocess.run(
        [
            "bash",
            _bash_runner_path(RUNNER_PATH),
            "--dry-run",
            "--shard",
            "S7-crosscutting-architecture",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    dry_run_lines = [
        line for line in result.stdout.splitlines() if line.startswith("[dry-run]")
    ]
    assert len(dry_run_lines) == 6
    assert any(r"test_\[c-z\]\*.py" in line for line in dry_run_lines)
    assert any(r"test_\[a-b\]\*.py" in line for line in dry_run_lines)
    assert any(r"test_\[d-z\]\*.py" in line for line in dry_run_lines)
    assert any(r"test_\[g-z\]\*.py" in line for line in dry_run_lines)
    assert any(r"test_\[a-f\]\*.py" in line for line in dry_run_lines)
    assert any(r"test_\[a-l\]\*.py" in line for line in dry_run_lines)
    assert any(r"test_\[a-r\]\*.py" in line for line in dry_run_lines)
