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


def test_scratch_path_rejects_escape_without_creating_files(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "ROOT", tmp_path / "repo")
    monkeypatch.setattr(runner.tempfile, "gettempdir", lambda: str(tmp_path / "temp"))
    outside = tmp_path / "repo" / "reports" / ".." / "outside"

    with pytest.raises(ValueError, match="Coverage scratch"):
        runner._scratch_path(outside)

    assert not outside.resolve().exists()


@pytest.mark.parametrize("folder", ("repo/reports/run", "temp/run"))
def test_scratch_path_allows_owned_output_roots(tmp_path, monkeypatch, folder):
    monkeypatch.setattr(runner, "ROOT", tmp_path / "repo")
    monkeypatch.setattr(runner.tempfile, "gettempdir", lambda: str(tmp_path / "temp"))

    assert runner._scratch_path(tmp_path / folder) == (tmp_path / folder).resolve()


def test_manifest_writer_does_not_overwrite_existing_temporary_file(tmp_path):
    temporary = tmp_path / "manifest.tmp"
    temporary.write_text("preserve existing evidence", encoding="utf-8")

    with pytest.raises(FileExistsError):
        runner._write_manifest(tmp_path / "manifest.json", {"complete": False})

    assert temporary.read_text(encoding="utf-8") == "preserve existing evidence"
    assert not (tmp_path / "manifest.json").exists()


def test_manifest_writer_rejects_arbitrary_name(tmp_path):
    with pytest.raises(ValueError, match="manifest name"):
        runner._write_manifest(tmp_path / "other.json", {})
    assert not (tmp_path / "other.json").exists()


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


def test_import_single_worker_shards_preserves_actual_commands(transported_shards):
    groups, scratch, expected, manifests = transported_shards
    expected["max_workers"] = 1
    by_name = {shard.name: shard for shard in SHARDS}
    for path in manifests:
        payload = json.loads(path.read_text())
        payload["max_workers"] = 1
        for row in payload["shards"]:
            row["command"] = _command(
                by_name[row["name"]], Path(row["junit_file"]), max_workers=1
            )
        path.write_text(json.dumps(payload))

    rows = import_shards(groups, scratch, expected)

    assert len(rows) == 17
    for row in rows:
        if by_name[row["name"]].parallel:
            assert row["command"][row["command"].index("-n") + 1] == "1"


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
        "workers",
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
    elif damage == "workers":
        payload["max_workers"] = 1
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
