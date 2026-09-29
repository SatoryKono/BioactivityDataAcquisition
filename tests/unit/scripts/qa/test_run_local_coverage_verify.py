"""Guards for the local, CI-independent coverage producer plan."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.engineering.qa.run_local_coverage_verify import SHARDS, _command, main

pytestmark = pytest.mark.unit

EXPECTED_SHARDS = (
    "smoke",
    "contract-confidence",
    "repo-backed-unit-product",
    "repo-backed-unit-tooling",
    "repo-backed-unit-ops",
    "unit-scripts-tooling-passport",
    "unit-scripts-tooling-debt-governance",
    "unit-scripts-tooling-other",
    "unit-filesystem-contracts",
    "unit-subprocess-backed",
    "unit-domain",
    "unit-application",
    "unit-infrastructure",
    "unit-other",
    "integration",
    "security",
    "serial",
)


def test_local_coverage_plan_has_all_required_producers() -> None:
    assert tuple(shard.name for shard in SHARDS) == EXPECTED_SHARDS
    assert len({shard.name for shard in SHARDS}) == 17
    assert all("tests/architecture" not in " ".join(shard.paths) for shard in SHARDS)


def test_local_coverage_commands_keep_shards_isolated() -> None:
    for shard in SHARDS:
        command = _command(shard, Path("junit.xml"))
        assert command[:3] == [
            "bash",
            "scripts/engineering/dev/run_pytest.sh",
            "--narrow",
        ]
        assert "--with-coverage" in command
        assert "--cov-report=" in command
        assert "--junitxml=junit.xml" in command
        if shard.parallel:
            assert command[command.index("-n") + 1] == "2"
        else:
            assert command[-2:] == ["-p", "no:xdist"]


def test_local_coverage_list_is_read_only(capsys) -> None:
    assert main(["--list"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 17
    assert lines[0].startswith("smoke:")
    assert lines[-1].startswith("serial:")
