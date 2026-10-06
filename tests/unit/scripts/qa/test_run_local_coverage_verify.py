"""Guards for the local, CI-independent coverage producer plan."""

from __future__ import annotations

from pathlib import Path
import json
import subprocess

import pytest

from scripts.engineering.qa import run_local_coverage_verify as runner
from scripts.engineering.qa.run_local_coverage_verify import (
    SHARDS,
    _command,
    _measurement_environment,
    main,
)

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
        assert Path(command[0]).name.lower() in {"bash", "bash.exe"}
        assert command[1:3] == [
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


@pytest.mark.parametrize("shard", SHARDS, ids=lambda shard: shard.name)
def test_single_worker_preserves_every_shard_selection_and_gate(shard) -> None:
    expected = _command(shard, Path("junit.xml"))
    if shard.parallel:
        expected[expected.index("-n") + 1] = "1"
    assert _command(shard, Path("junit.xml"), max_workers=1) == expected


@pytest.mark.parametrize("workers", ("0", "3", "-1"))
def test_worker_limit_cannot_disable_execution_or_raise_resource_budget(
    workers,
) -> None:
    with pytest.raises(SystemExit) as error:
        main(["--list", "--max-workers", workers])
    assert error.value.code == 2


def test_single_worker_is_recorded_and_used_without_accepting_failed_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        runner, "_git", lambda *args: "" if args[0] == "status" else "a" * 40
    )
    monkeypatch.setattr(runner, "compute_source_tree_sha256", lambda **kwargs: "b" * 64)
    monkeypatch.setattr(
        runner, "compute_test_telemetry_source_tree_sha256", lambda **kwargs: "c" * 64
    )
    executed = []

    def failed_shard(command, log, *, env):
        executed.append(command)
        return 1

    monkeypatch.setattr(runner, "_run_logged", failed_shard)
    scratch = tmp_path / "measurement"
    assert main(["--scratch-dir", str(scratch), "--max-workers", "1"]) == 1
    manifest = json.loads((scratch / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["max_workers"] == 1
    assert manifest["complete"] is False
    assert len(executed) == len(manifest["shards"]) == 17
    for shard, command, row in zip(SHARDS, executed, manifest["shards"], strict=True):
        assert row["command"] == command
        assert row["exit_code"] == 1
        if shard.parallel:
            assert command[command.index("-n") + 1] == "1"
        else:
            assert command[-2:] == ["-p", "no:xdist"]


@pytest.mark.subprocess_backed
def test_temporary_git_fixture_cannot_overwrite_callers_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    foreign_index = tmp_path / "foreign-index"
    foreign_index.write_bytes(b"caller index must remain untouched")
    monkeypatch.setenv("GIT_INDEX_FILE", str(foreign_index))
    monkeypatch.setenv("GIT_WORK_TREE", str(tmp_path / "foreign-worktree"))
    monkeypatch.setenv("WSLENV", "GIT_INDEX_FILE/p:PYTHONUTF8:GIT_WORK_TREE/p")
    env = _measurement_environment()
    repo = tmp_path / "fixture"
    repo.mkdir()
    for args in (("init", "-q"), ("read-tree", "--empty")):
        subprocess.run(
            ["git", *args],
            cwd=repo,
            env=env,
            check=True,
            capture_output=True,
            timeout=20,
        )
    assert foreign_index.read_bytes() == b"caller index must remain untouched"
    assert (repo / ".git" / "index").is_file()
    assert env["WSLENV"] == "PYTHONUTF8"
