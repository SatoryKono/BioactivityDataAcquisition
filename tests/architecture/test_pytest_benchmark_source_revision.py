# pyright: reportArgumentType=false
"""CF-039: gitdir source revision without a Git or Mercurial subprocess."""

from __future__ import annotations

import json
import os
import subprocess
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
    """Create a git metadata file and its parents."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _measurement(path: Path, revision: str) -> None:
    """Write a minimal measurement JSON for the given revision."""
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
    """The checkout reads the expected commit and the validator accepts that JSON."""
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
    """Unreadable HEAD is blocked and the validator rejects a foreign revision."""
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
    """A symbolic HEAD resolves to the loose ref commit."""
    root = tmp_path / "checkout"
    _write(root / ".git" / "HEAD", "ref: refs/heads/topic\n")
    _write(root / ".git" / "refs" / "heads" / "topic", COMMIT + "\n")
    _assert_commit(root, COMMIT, "refs/heads/topic")


def test_detached_head_is_raw_commit(tmp_path: Path) -> None:
    """A detached HEAD is the raw commit, not a branch name."""
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
    """A symbolic HEAD resolves through packed-refs."""
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
    """A linked worktree reads the commit from the common git directory."""
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


def test_uppercase_head_marker_is_blocked(tmp_path: Path) -> None:
    """A HEAD marker other than the exact prefix ref: is blocked."""
    root = tmp_path / "uppercase-head"
    _write(root / ".git" / "HEAD", "REF: refs/heads/topic\n")
    _write(root / ".git" / "refs" / "heads" / "topic", COMMIT + "\n")
    _assert_blocked(root)


def test_uppercase_gitdir_marker_is_blocked(tmp_path: Path) -> None:
    """A linked gitfile marker other than the exact prefix gitdir: is blocked."""
    checkout = tmp_path / "linked"
    _write(checkout / ".git", "GITDIR: ../repo.git\n")
    _write(tmp_path / "repo.git" / "HEAD", COMMIT + "\n")
    _assert_blocked(checkout)


def test_malformed_packed_refs_line_does_not_yield_a_later_sha(tmp_path: Path) -> None:
    """A malformed packed-refs line rejects the file, including a later SHA."""
    root = tmp_path / "malformed-packed"
    _write(root / ".git" / "HEAD", "ref: refs/heads/topic\n")
    _write(
        root / ".git" / "packed-refs",
        f"not-a-packed-line\n{PACKED} refs/heads/topic\n",
    )
    source = read_source_revision(root, allow_parent_search=False)
    assert source.revision == "unknown"
    assert source.revision != PACKED
    assert source.revision_method == "blocked"


def test_worktree_private_packed_refs_do_not_hide_the_common_ref(
    tmp_path: Path,
) -> None:
    """A private worktree packed-refs file does not override the common gitdir."""
    common = tmp_path / "repo.git"
    worktree_git = common / "worktrees" / "linked"
    checkout = tmp_path / "linked"
    _write(checkout / ".git", "gitdir: ../repo.git/worktrees/linked\n")
    _write(worktree_git / "HEAD", "ref: refs/heads/topic\n")
    _write(worktree_git / "commondir", "../..\n")
    _write(worktree_git / "packed-refs", f"{PACKED} refs/heads/topic\n")
    _write(common / "packed-refs", f"{COMMIT} refs/heads/topic\n")
    _assert_commit(checkout, COMMIT, "refs/heads/topic")


def test_missing_commondir_target_blocks_detached_worktree_head(
    tmp_path: Path,
) -> None:
    """A missing commondir directory does not accept the private detached HEAD."""
    common = tmp_path / "repo.git"
    worktree_git = common / "worktrees" / "linked"
    checkout = tmp_path / "linked"
    _write(checkout / ".git", "gitdir: ../repo.git/worktrees/linked\n")
    _write(worktree_git / "HEAD", COMMIT + "\n")
    _write(worktree_git / "commondir", "../missing\n")
    _assert_blocked(checkout)


def test_missing_head_is_blocked(tmp_path: Path) -> None:
    """A gitdir without HEAD is blocked."""
    root = tmp_path / "missing"
    _write(root / ".git" / "config", "[core]\n")
    _assert_blocked(root)


def test_corrupt_head_is_blocked(tmp_path: Path) -> None:
    """A HEAD that is neither a ref nor a SHA is blocked."""
    root = tmp_path / "corrupt"
    _write(root / ".git" / "HEAD", "not-a-ref\n")
    _assert_blocked(root)


def test_unresolvable_symbolic_head_is_blocked(tmp_path: Path) -> None:
    """A symbolic HEAD whose ref is missing is blocked."""
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
    """Boolean round counts and an unspecified caller fail validation."""
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


def test_symlink_loop_is_blocked_without_vcs_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A symlink loop is blocked and does not call Git or Mercurial."""
    loop = tmp_path / "loop"
    try:
        os.symlink(loop, loop, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink loop is not available: {exc}")
    calls: list[object] = []

    def _record(*args: object, **kwargs: object) -> None:
        """Record a forbidden VCS subprocess call."""
        calls.append((args, kwargs))
        raise AssertionError("VCS subprocess is not a fallback")

    monkeypatch.setattr(subprocess, "run", _record)
    monkeypatch.setattr(subprocess, "check_output", _record)
    monkeypatch.setattr(subprocess, "check_call", _record)
    monkeypatch.setattr(subprocess, "call", _record)
    source = read_source_revision(loop, allow_parent_search=False)
    assert source.revision == "unknown"
    assert source.revision_method == "blocked"
    assert calls == []


def test_broken_symlink_loose_ref_does_not_fall_back_to_packed_refs(
    tmp_path: Path,
) -> None:
    """A broken loose-ref symlink does not fall back to packed-refs."""
    root = tmp_path / "checkout"
    ref_path = root / ".git" / "refs" / "heads" / "topic"
    _write(root / ".git" / "HEAD", "ref: refs/heads/topic\n")
    _write(root / ".git" / "packed-refs", f"{PACKED} refs/heads/topic\n")
    ref_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.symlink(ref_path.parent / "missing", ref_path)
    except OSError as exc:
        pytest.skip(f"symlink is not available: {exc}")
    source = read_source_revision(root, allow_parent_search=False)
    assert source.revision == "unknown"
    assert source.revision != PACKED
    assert source.revision_method == "blocked"


def test_unreadable_loose_ref_directory_does_not_fall_back_to_packed_refs(
    tmp_path: Path,
) -> None:
    """A directory standing in for a loose ref does not fall back to packed-refs."""
    root = tmp_path / "checkout"
    _write(root / ".git" / "HEAD", "ref: refs/heads/topic\n")
    _write(root / ".git" / "packed-refs", f"{PACKED} refs/heads/topic\n")
    topic = root / ".git" / "refs" / "heads" / "topic"
    topic.mkdir(parents=True)
    source = read_source_revision(root, allow_parent_search=False)
    assert source.revision == "unknown"
    assert source.revision != PACKED
    assert source.revision_method == "blocked"


def test_corrupt_loose_ref_does_not_fall_back_to_packed_refs(tmp_path: Path) -> None:
    """A corrupt loose ref does not fall back to packed-refs."""
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


@pytest.mark.parametrize("marker", ["REF:", "Ref:", "ref:", "REF: ", "Ref: ", " ref: "])
def test_malformed_head_marker_is_blocked(tmp_path: Path, marker: str) -> None:
    """Git markers are case-sensitive and require a separating space."""
    _write(tmp_path / ".git/HEAD", f"{marker}refs/heads/topic\n")
    _write(tmp_path / ".git/refs/heads/topic", COMMIT)
    _assert_blocked(tmp_path)


@pytest.mark.parametrize(
    "value", ["", "GITDIR: metadata", "gitdir:", "gitdir: metadata\nextra"]
)
def test_malformed_gitdir_file_is_blocked(tmp_path: Path, value: str) -> None:
    """A malformed gitfile cannot claim the commit of a plausible directory."""
    _write(tmp_path / ".git", value)
    _write(tmp_path / "metadata/HEAD", COMMIT)
    _assert_blocked(tmp_path)


@pytest.mark.parametrize("value", ["", "missing", "../missing", "../common\nextra"])
def test_invalid_commondir_blocks_detached_head(tmp_path: Path, value: str) -> None:
    """Present but invalid commondir metadata is never treated as absent."""
    _write(tmp_path / ".git/HEAD", COMMIT)
    _write(tmp_path / ".git/commondir", value)
    _assert_blocked(tmp_path)


@pytest.mark.parametrize("cyclic", [False, True])
@pytest.mark.parametrize("entry", ["refs/heads/topic", "commondir", "packed-refs"])
def test_broken_metadata_symlinks_block_stale_fallback(
    tmp_path: Path, cyclic: bool, entry: str
) -> None:
    """Broken and cyclic metadata links cannot expose a packed commit."""
    _write(tmp_path / ".git/HEAD", "ref: refs/heads/topic\n")
    if entry != "packed-refs":
        _write(tmp_path / ".git/packed-refs", f"{PACKED} refs/heads/topic\n")
    link = tmp_path / ".git" / entry
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(link if cyclic else tmp_path / "missing")
    _assert_blocked(tmp_path)


@pytest.mark.parametrize(
    "bad", ["garbage", "", "^broken", "^" + COMMIT, COMMIT + " refs/heads/topic"]
)
def test_malformed_packed_refs_block_even_after_matching_row(
    tmp_path: Path, bad: str
) -> None:
    """All packed rows must be valid, including duplicates and peeled records."""
    _write(tmp_path / ".git/HEAD", "ref: refs/heads/topic\n")
    _write(
        tmp_path / ".git/packed-refs", f"{COMMIT} refs/heads/topic\n^{COMMIT}\n{bad}\n"
    )
    _assert_blocked(tmp_path)


def test_common_ref_ignores_stale_private_packed_refs(tmp_path: Path) -> None:
    """A linked worktree's shared branch belongs exclusively to commondir."""
    _write(tmp_path / ".git/HEAD", "ref: refs/heads/topic\n")
    _write(tmp_path / ".git/commondir", "../common\n")
    _write(tmp_path / ".git/packed-refs", f"{PACKED} refs/heads/topic\n")
    _write(tmp_path / "common/packed-refs", f"{COMMIT} refs/heads/topic\n")
    _assert_commit(tmp_path, COMMIT, "refs/heads/topic")
    (tmp_path / "common/packed-refs").unlink()
    _assert_blocked(tmp_path)


@pytest.mark.parametrize("value", ["REF: refs/heads/other", "Ref: refs/heads/other"])
def test_loose_ref_marker_is_case_sensitive(tmp_path: Path, value: str) -> None:
    """A mixed-case symbolic loose ref is corrupt even with a valid target."""
    _write(tmp_path / ".git/HEAD", "ref: refs/heads/topic\n")
    _write(tmp_path / ".git/refs/heads/topic", value)
    _write(tmp_path / ".git/refs/heads/other", COMMIT)
    _assert_blocked(tmp_path)


def test_cyclic_symbolic_refs_do_not_fall_back(tmp_path: Path) -> None:
    """A symbolic ref cycle is blocked even if packed refs contain a commit."""
    _write(tmp_path / ".git/HEAD", "ref: refs/heads/a\n")
    _write(tmp_path / ".git/refs/heads/a", "ref: refs/heads/b\n")
    _write(tmp_path / ".git/refs/heads/b", "ref: refs/heads/a\n")
    _write(tmp_path / ".git/packed-refs", f"{COMMIT} refs/heads/a\n")
    _assert_blocked(tmp_path)


@pytest.mark.parametrize("cyclic", [False, True])
def test_broken_gitfile_symlink_blocks_parent_search(
    tmp_path: Path, cyclic: bool
) -> None:
    """An invalid child checkout must not borrow the parent repository's HEAD."""
    _write(tmp_path / ".git/HEAD", COMMIT)
    child = tmp_path / "child"
    child.mkdir()
    link = child / ".git"
    link.symlink_to(link if cyclic else tmp_path / "missing")
    assert read_source_revision(child).blocked
