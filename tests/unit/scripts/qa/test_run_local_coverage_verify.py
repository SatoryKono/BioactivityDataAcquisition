"""Guards for the local, CI-independent coverage producer plan."""

from __future__ import annotations

from pathlib import Path
import subprocess
import json

import pytest

from scripts.engineering.qa.run_local_coverage_verify import (
    SHARDS,
    _command,
    _measurement_environment,
    main,
    import_shards,
    _sha256,
)
from scripts.engineering.ci.local_test_telemetry import junit_telemetry_sha256

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


@pytest.fixture()
def transported_shards(tmp_path):
    groups = tmp_path / "groups"
    expected = {
        "head": "a" * 40,
        "source_tree_sha256": "b" * 64,
        "test_tree_sha256": "c" * 64,
        "python": "3.12.0",
        "ci_workflow_id": "workflow-1",
        "required_shards": [s.name for s in SHARDS],
    }
    manifests = []
    for index in range(4):
        folder = groups / f"coverage-{index}/measurement"
        folder.mkdir(parents=True)
        for subdir in ("shards", "junit", "logs"):
            (folder / subdir).mkdir()
        rows = []
        for shard in SHARDS[index::4]:
            coverage = folder / "shards" / f".coverage.{shard.name}"
            coverage.write_bytes(b"coverage evidence")
            junit = folder / "junit" / f"{shard.name}.xml"
            junit.write_text(
                '<testsuite><testcase name="passing" time="1"/></testsuite>'
            )
            log = folder / "logs" / f"{shard.name}.log"
            log.write_text("passed")
            rows.append(
                {
                    "name": shard.name,
                    "command": _command(shard, junit),
                    "exit_code": 0,
                    "coverage_file": str(coverage),
                    "coverage_sha256": _sha256(coverage),
                    "junit_file": str(junit),
                    "junit_telemetry_sha256": junit_telemetry_sha256(junit),
                    "log_file": str(log),
                    "seconds": 1,
                }
            )
        manifest = folder / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    **expected,
                    "scratch_dir": str(folder),
                    "shards_complete": True,
                    "shards": rows,
                }
            )
        )
        manifests.append(manifest)
    scratch = tmp_path / "combined"
    for name in ("shards", "junit", "logs"):
        (scratch / name).mkdir(parents=True)
    return groups, scratch, expected, manifests


def test_import_all_shards_without_executing_tests(transported_shards, monkeypatch):
    groups, scratch, expected, _ = transported_shards
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **kw: pytest.fail("Must not rerun tests")
    )
    rows = import_shards(groups, scratch, expected)
    assert [row["name"] for row in rows] == list(EXPECTED_SHARDS)
    assert all(Path(row["junit_file"]).is_relative_to(scratch) for row in rows)


@pytest.mark.parametrize(
    "damage",
    [
        "missing",
        "duplicate",
        "sha",
        "workflow",
        "digest",
        "failed",
        "selector",
        "junit",
    ],
)
def test_import_rejects_invalid_shard_evidence(transported_shards, damage):
    groups, scratch, expected, manifests = transported_shards
    manifest = manifests[0]
    payload = json.loads(manifest.read_text())
    row = payload["shards"][0]
    if damage == "missing":
        payload["shards"].pop()
    elif damage == "duplicate":
        payload["shards"].append(row.copy())
    elif damage == "sha":
        payload["head"] = "d" * 40
    elif damage == "workflow":
        payload["ci_workflow_id"] = "other"
    elif damage == "digest":
        Path(row["coverage_file"]).write_bytes(b"tampered")
    elif damage == "failed":
        row["exit_code"] = 1
    elif damage == "selector":
        row["command"] = ["true"]
    else:
        Path(row["junit_file"]).write_text(
            "<testsuite><testcase><failure/></testcase></testsuite>"
        )
        row["junit_telemetry_sha256"] = junit_telemetry_sha256(Path(row["junit_file"]))
    manifest.write_text(json.dumps(payload))
    with pytest.raises(ValueError):
        import_shards(groups, scratch, expected)


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
