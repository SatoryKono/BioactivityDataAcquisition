# pyright: reportArgumentType=false
"""CF-039: gitdir source revision without a Git or Mercurial subprocess."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.benchmarks.benchmark_vcs_guard import (
    BenchmarkMeasurementContractError,
    read_source_revision,
    validate_benchmark_measurement_json,
)

pytestmark = pytest.mark.architecture

COMMIT = "40fa210b9279c5a10568783815230a8955cc1d02"
PACKED = "0123456789abcdef0123456789abcdef01234567"
RUN_ID = "11111111-1111-4111-8111-111111111111"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _measurement(path: Path, revision: str) -> None:
    payload = {
        "benchmarks": [{"stats": {"rounds": 1}}],
        "commit_info": {"id": revision, "dirty": None},
        "bioetl_source": {
            "schema_version": 1,
            "revision": revision,
            "revision_method": "gitdir_head_file",
            "dirty_state": "unknown",
        },
        "bioetl_run": {
            "id": RUN_ID,
            "kind": "pytest-benchmark",
            "caller": "synthetic-proof",
        },
        "bioetl_vcs_guard": {
            "installed_before_plugin": True,
            "blocked_probe_attempts": 0,
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _assert_commit(source_root: Path, revision: str, branch: str) -> None:
    source = read_source_revision(source_root, allow_parent_search=False)
    assert source.revision == revision
    assert source.revision != branch.rsplit("/", 1)[-1]
    assert source.revision_method == "gitdir_head_file"
    assert source.dirty_state == "unknown"
    assert source.branch == branch
    output = source_root / "measurement.json"
    _measurement(output, revision)
    validate_benchmark_measurement_json(output, search_from=source_root)


def _assert_blocked(source_root: Path) -> None:
    source = read_source_revision(source_root, allow_parent_search=False)
    assert source.revision == "unknown"
    assert source.revision_method == "blocked"
    assert source.dirty_state == "unknown"
    output = source_root / "measurement.json"
    _measurement(output, COMMIT)
    with pytest.raises(BenchmarkMeasurementContractError) as error:
        validate_benchmark_measurement_json(output, search_from=source_root)
    assert error.value.code == "provenance_mismatch"


def test_ordinary_checkout_symbolic_head_is_commit(tmp_path: Path) -> None:
    root = tmp_path / "checkout"
    _write(root / ".git" / "HEAD", "ref: refs/heads/topic\n")
    _write(root / ".git" / "refs" / "heads" / "topic", COMMIT + "\n")
    _assert_commit(root, COMMIT, "refs/heads/topic")


def test_detached_head_is_raw_commit(tmp_path: Path) -> None:
    root = tmp_path / "detached"
    _write(root / ".git" / "HEAD", COMMIT.upper() + "\n")
    source = read_source_revision(root, allow_parent_search=False)
    assert source.revision == COMMIT
    assert source.branch == "(detached head)"
    assert source.dirty_state == "unknown"
    output = root / "measurement.json"
    _measurement(output, COMMIT)
    validate_benchmark_measurement_json(output, search_from=root)


def test_packed_refs_resolve_to_commit(tmp_path: Path) -> None:
    root = tmp_path / "packed"
    _write(root / ".git" / "HEAD", "ref: refs/heads/topic\n")
    _write(
        root / ".git" / "packed-refs",
        "# pack-refs with: peeled fully-peeled\n"
        f"{PACKED.upper()} refs/heads/topic\n"
        f"^{'c' * 40}\n",
    )
    _assert_commit(root, PACKED, "refs/heads/topic")


def test_linked_worktree_uses_common_git_directory(tmp_path: Path) -> None:
    common = tmp_path / "repo.git"
    worktree_git = common / "worktrees" / "linked"
    checkout = tmp_path / "linked"
    _write(checkout / ".git", "gitdir: ../repo.git/worktrees/linked\n")
    _write(worktree_git / "HEAD", "ref: refs/heads/topic\n")
    _write(worktree_git / "commondir", "../..\n")
    _write(
        common / "packed-refs",
        f"{COMMIT} refs/heads/topic\n",
    )
    _assert_commit(checkout, COMMIT, "refs/heads/topic")


def test_missing_head_is_blocked(tmp_path: Path) -> None:
    root = tmp_path / "missing"
    _write(root / ".git" / "config", "[core]\n")
    _assert_blocked(root)


def test_corrupt_head_is_blocked(tmp_path: Path) -> None:
    root = tmp_path / "corrupt"
    _write(root / ".git" / "HEAD", "not-a-ref\n")
    _assert_blocked(root)


def test_unresolvable_symbolic_head_is_blocked(tmp_path: Path) -> None:
    root = tmp_path / "dangling"
    _write(root / ".git" / "HEAD", "ref: refs/heads/missing\n")
    source = read_source_revision(root, allow_parent_search=False)
    assert source.revision == "unknown"
    assert source.branch == "refs/heads/missing"
    assert source.revision_method == "blocked"
    output = root / "measurement.json"
    _measurement(output, COMMIT)
    with pytest.raises(BenchmarkMeasurementContractError) as error:
        validate_benchmark_measurement_json(output, search_from=root)
    assert error.value.code == "provenance_mismatch"


def test_validator_rejects_bool_counts_and_unspecified_caller(tmp_path: Path) -> None:
    root = tmp_path / "checkout"
    _write(root / ".git" / "HEAD", COMMIT + "\n")
    output = root / "measurement.json"
    _measurement(output, COMMIT)
    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["benchmarks"][0]["stats"]["rounds"] = True
    output.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(BenchmarkMeasurementContractError) as rounds_error:
        validate_benchmark_measurement_json(output, search_from=root)
    assert rounds_error.value.code == "no_measurements"

    payload["benchmarks"][0]["stats"]["rounds"] = 1
    payload["bioetl_source"]["schema_version"] = True
    output.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(BenchmarkMeasurementContractError) as schema_error:
        validate_benchmark_measurement_json(output, search_from=root)
    assert schema_error.value.code == "blocked_provenance"

    payload["bioetl_source"]["schema_version"] = 1
    payload["bioetl_vcs_guard"]["blocked_probe_attempts"] = True
    output.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(BenchmarkMeasurementContractError) as probes_error:
        validate_benchmark_measurement_json(output, search_from=root)
    assert probes_error.value.code == "vcs_probe"

    payload["bioetl_vcs_guard"]["blocked_probe_attempts"] = 0
    payload["bioetl_run"]["caller"] = "unspecified"
    output.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(BenchmarkMeasurementContractError) as caller_error:
        validate_benchmark_measurement_json(output, search_from=root)
    assert caller_error.value.code == "blocked_provenance"


def test_corrupt_loose_ref_does_not_fall_back_to_packed_refs(tmp_path: Path) -> None:
    root = tmp_path / "checkout"
    _write(root / ".git" / "HEAD", "ref: refs/heads/topic\n")
    _write(root / ".git" / "refs" / "heads" / "topic", "corrupt\n")
    _write(root / ".git" / "packed-refs", f"{PACKED} refs/heads/topic\n")
    source = read_source_revision(root, allow_parent_search=False)
    assert source.revision == "unknown"
    assert source.revision != PACKED
    assert source.revision_method == "blocked"
    output = root / "measurement.json"
    _measurement(output, PACKED)
    with pytest.raises(BenchmarkMeasurementContractError) as error:
        validate_benchmark_measurement_json(output, search_from=root)
    assert error.value.code == "provenance_mismatch"
