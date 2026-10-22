from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from collections.abc import Callable
from collections.abc import Generator
from pathlib import Path

import pytest

from scripts.engineering.qa.verify_quality_move import main as verify_quality_move_main

_GIT_LOCATION_VARS = frozenset(
    {
        "GIT_COMMON_DIR",
        "GIT_DIR",
        "GIT_INDEX_FILE",
        "GIT_NAMESPACE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_WORK_TREE",
    }
)
_ROW_COUNT = 30
_HEADER = (
    "source_path,target_path,blob_sha,base_commit,"
    "snapshot_relation_prior,evidence_status,required_changes,acceptance\n"
)
Runner = Callable[[str, str, str, str, str, str], subprocess.CompletedProcess[str]]


def _git_env() -> dict[str, str]:
    return {
        key: value for key, value in os.environ.items() if key not in _GIT_LOCATION_VARS
    }


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        env=_git_env(),
        timeout=60,
    )


def _source(index: int) -> str:
    return f"src/bioetl/test{index}.py"


def _target(index: int) -> str:
    return f"scripts/engineering/qa/test{index}.py"


def _write_sources(repo: Path) -> None:
    for index in range(_ROW_COUNT):
        path = repo / _source(index)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("code", encoding="utf-8")


def _commit_all(repo: Path, message: str) -> str:
    git(repo, "add", "-A")
    git(repo, "commit", "-m", message)
    return git(repo, "rev-parse", "HEAD").stdout.strip()


def _blob(repo: Path, commit: str, relative: str) -> str:
    return git(repo, "rev-parse", f"{commit}:{relative}").stdout.strip()


def _head_tree(repo: Path) -> str:
    return git(repo, "rev-parse", "HEAD^{tree}").stdout.strip()


def _removed_decision() -> dict[str, str]:
    return {
        "path": "tests/test_x.py",
        "literal": "bioetl.foo",
        "context": "import",
        "purpose": "test",
        "owner": "QM-03",
        "reviewed_content_sha256": "x",
        "review_by": "QM-01",
        "status": "removed",
    }


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_loose_manifest(
    path: Path,
    *,
    rows: int = _ROW_COUNT,
    dup_source: bool = False,
    dup_target: bool = False,
    invalid_cols: bool = False,
    bad_prefix: bool = False,
    blob: str = "sha",
    base: str = "base",
    short_row: bool = False,
    extra_cell: bool = False,
    traversal: bool = False,
) -> None:
    header = "source_path,target_path,blob_sha\n" if invalid_cols else _HEADER
    lines = [header]
    for index in range(rows):
        source = _source(0 if dup_source and index == 1 else index)
        target = _target(0 if dup_target and index == 1 else index)
        if bad_prefix:
            source = f"bioetl/test{index}.py"
        if traversal and index == 0:
            source = "src/../outside.py"
        if invalid_cols:
            lines.append(f"{source},{target},{blob}\n")
            continue
        cells = f"{source},{target},{blob},{base},rel,status,changes,acc"
        if short_row and index == 0:
            cells = f"{source},{target}"
        if extra_cell and index == 0:
            cells = f"{cells},extra"
        lines.append(f"{cells}\n")
    path.write_text("".join(lines), encoding="utf-8")


def _write_bound_manifest(
    path: Path,
    repo: Path,
    commit: str,
    *,
    blob_override: str | None = None,
) -> None:
    lines = [_HEADER]
    for index in range(_ROW_COUNT):
        source = _source(index)
        digest = blob_override or _blob(repo, commit, source)
        lines.append(
            f"{source},{_target(index)},{digest},{commit},rel,status,changes,acc\n"
        )
    path.write_text("".join(lines), encoding="utf-8")


def _write_evidence(
    path: Path, repo: Path, phase: str, *, tree: str | None = None
) -> None:
    _write_json(
        path,
        {
            "status": "PASS",
            "tree": _head_tree(repo) if tree is None else tree,
            "phase": phase,
        },
    )


def _commit_move(
    repo: Path,
    *,
    keep_source: bool = False,
    extra: dict[str, str] | None = None,
) -> str:
    for index in range(_ROW_COUNT):
        target = repo / _target(index)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("code", encoding="utf-8")
        if not keep_source:
            git(repo, "rm", "-f", _source(index))
    for relative, text in (extra or {}).items():
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return _commit_all(repo, "move")


def _invoke(
    run_scanner: Runner,
    repo: Path,
    tmp_path: Path,
    phase: str,
    manifest: Path,
    decisions: Path,
    evidence: Path,
    *,
    out_name: str = "out",
) -> subprocess.CompletedProcess[str]:
    return run_scanner(
        phase,
        str(manifest),
        str(decisions),
        str(evidence),
        str(repo),
        str(tmp_path / out_name),
    )


@pytest.fixture
def run_scanner() -> Runner:
    def _run_scanner(
        phase: str,
        manifest_path: str,
        decisions_path: str,
        evidence_path: str,
        repo: str,
        out_dir: str,
    ) -> subprocess.CompletedProcess[str]:
        env = _git_env()
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[5])
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "scripts.engineering.qa.verify_quality_move",
                "--phase",
                phase,
                "--repo",
                repo,
                "--manifest-path",
                manifest_path,
                "--decisions-path",
                decisions_path,
                "--evidence-path",
                evidence_path,
                "--out-dir",
                out_dir,
            ],
            capture_output=True,
            text=True,
            env=env,
            timeout=60,
        )

    return _run_scanner


@pytest.fixture
def synthetic_repo(tmp_path: Path) -> Generator[Path, None, None]:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test User")
    yield repo


@pytest.fixture
def committed_sources(synthetic_repo: Path) -> tuple[Path, str]:
    _write_sources(synthetic_repo)
    return synthetic_repo, _commit_all(synthetic_repo, "sources")


def _removed(path: Path, payload: object | None = None) -> Path:
    _write_json(path, [_removed_decision()] if payload is None else payload)
    return path


@pytest.mark.unit
def test_missing_evidence(
    run_scanner: Runner,
    committed_sources: tuple[Path, str],
    tmp_path: Path,
) -> None:
    repo, commit = committed_sources
    manifest = tmp_path / "manifest.csv"
    _write_bound_manifest(manifest, repo, commit)
    decisions = _removed(tmp_path / "decisions.json")
    out_dir = tmp_path / "out"
    res = _invoke(
        run_scanner,
        repo,
        tmp_path,
        "before",
        manifest,
        decisions,
        tmp_path / "missing.json",
    )
    assert res.returncode == 1
    assert "Missing evidence path" in res.stdout
    evidence = json.loads(
        (out_dir / "execution_evidence.json").read_text(encoding="utf-8")
    )
    assert evidence["status"] == "NOT_RUN"
    assert evidence["phase"] == "before"
    assert evidence["input_hashes"]["evidence"] == ""


@pytest.mark.unit
def test_invalid_csv_schema(
    run_scanner: Runner, synthetic_repo: Path, tmp_path: Path
) -> None:
    manifest = tmp_path / "manifest.csv"
    _write_loose_manifest(manifest, invalid_cols=True)
    res = _invoke(
        run_scanner,
        synthetic_repo,
        tmp_path,
        "before",
        manifest,
        tmp_path / "decisions.json",
        tmp_path / "evidence.json",
    )
    assert res.returncode == 1
    assert "Manifest Error: Missing columns" in res.stdout
    evidence = json.loads(
        (tmp_path / "out" / "execution_evidence.json").read_text(encoding="utf-8")
    )
    assert evidence["status"] == "BLOCKED"


@pytest.mark.unit
def test_wrong_row_count(
    run_scanner: Runner, synthetic_repo: Path, tmp_path: Path
) -> None:
    manifest = tmp_path / "manifest.csv"
    _write_loose_manifest(manifest, rows=29)
    res = _invoke(
        run_scanner,
        synthetic_repo,
        tmp_path,
        "before",
        manifest,
        tmp_path / "decisions.json",
        tmp_path / "evidence.json",
    )
    assert res.returncode == 1
    assert "Expected exactly 30 rows" in res.stdout


@pytest.mark.unit
def test_duplicate_source(
    run_scanner: Runner, synthetic_repo: Path, tmp_path: Path
) -> None:
    manifest = tmp_path / "manifest.csv"
    _write_loose_manifest(manifest, dup_source=True)
    res = _invoke(
        run_scanner,
        synthetic_repo,
        tmp_path,
        "before",
        manifest,
        tmp_path / "decisions.json",
        tmp_path / "evidence.json",
    )
    assert res.returncode == 1
    assert "Duplicate source_path" in res.stdout


@pytest.mark.unit
def test_duplicate_target(
    run_scanner: Runner, synthetic_repo: Path, tmp_path: Path
) -> None:
    manifest = tmp_path / "manifest.csv"
    _write_loose_manifest(manifest, dup_target=True)
    res = _invoke(
        run_scanner,
        synthetic_repo,
        tmp_path,
        "before",
        manifest,
        tmp_path / "decisions.json",
        tmp_path / "evidence.json",
    )
    assert res.returncode == 1
    assert "Duplicate target_path" in res.stdout


@pytest.mark.unit
def test_short_manifest_row(
    run_scanner: Runner, synthetic_repo: Path, tmp_path: Path
) -> None:
    manifest = tmp_path / "manifest.csv"
    _write_loose_manifest(manifest, short_row=True)
    res = _invoke(
        run_scanner,
        synthetic_repo,
        tmp_path,
        "before",
        manifest,
        tmp_path / "decisions.json",
        tmp_path / "evidence.json",
    )
    assert res.returncode == 1
    assert "Manifest row missing" in res.stdout


@pytest.mark.unit
def test_extra_manifest_cell(
    run_scanner: Runner, synthetic_repo: Path, tmp_path: Path
) -> None:
    manifest = tmp_path / "manifest.csv"
    _write_loose_manifest(manifest, extra_cell=True)
    res = _invoke(
        run_scanner,
        synthetic_repo,
        tmp_path,
        "before",
        manifest,
        tmp_path / "decisions.json",
        tmp_path / "evidence.json",
    )
    assert res.returncode == 1
    assert "Manifest row has extra cells" in res.stdout


@pytest.mark.unit
def test_non_hex_blob_and_base(
    run_scanner: Runner, synthetic_repo: Path, tmp_path: Path
) -> None:
    manifest = tmp_path / "manifest.csv"
    _write_loose_manifest(manifest, blob="sha")
    blob_result = _invoke(
        run_scanner,
        synthetic_repo,
        tmp_path,
        "before",
        manifest,
        tmp_path / "decisions.json",
        tmp_path / "evidence.json",
        out_name="blob-out",
    )
    assert blob_result.returncode == 1
    assert "blob_sha must be 40 hex characters" in blob_result.stdout
    _write_loose_manifest(manifest, blob="a" * 40, base="base")
    base_result = _invoke(
        run_scanner,
        synthetic_repo,
        tmp_path,
        "before",
        manifest,
        tmp_path / "decisions.json",
        tmp_path / "evidence.json",
        out_name="base-out",
    )
    assert base_result.returncode == 1
    assert "base_commit must be 40 hex characters" in base_result.stdout


@pytest.mark.unit
def test_blob_sha_mismatch(
    run_scanner: Runner,
    committed_sources: tuple[Path, str],
    tmp_path: Path,
) -> None:
    repo, commit = committed_sources
    manifest = tmp_path / "manifest.csv"
    _write_bound_manifest(manifest, repo, commit, blob_override="0" * 40)
    res = _invoke(
        run_scanner,
        repo,
        tmp_path,
        "before",
        manifest,
        tmp_path / "decisions.json",
        tmp_path / "evidence.json",
    )
    assert res.returncode == 1
    assert "blob_sha mismatch" in res.stdout


@pytest.mark.unit
def test_path_traversal(
    run_scanner: Runner, synthetic_repo: Path, tmp_path: Path
) -> None:
    manifest = tmp_path / "manifest.csv"
    _write_loose_manifest(manifest, traversal=True)
    res = _invoke(
        run_scanner,
        synthetic_repo,
        tmp_path,
        "before",
        manifest,
        tmp_path / "decisions.json",
        tmp_path / "evidence.json",
    )
    assert res.returncode == 1
    assert "Path traversal detected" in res.stdout


@pytest.mark.unit
def test_wrong_evidence_tree(
    run_scanner: Runner,
    committed_sources: tuple[Path, str],
    tmp_path: Path,
) -> None:
    repo, commit = committed_sources
    manifest = tmp_path / "manifest.csv"
    _write_bound_manifest(manifest, repo, commit)
    decisions = _removed(tmp_path / "decisions.json")
    evidence = tmp_path / "evidence.json"
    _write_evidence(evidence, repo, "before")
    (repo / "other.txt").write_text("hey", encoding="utf-8")
    _commit_all(repo, "update")
    res = _invoke(run_scanner, repo, tmp_path, "before", manifest, decisions, evidence)
    assert res.returncode == 1
    assert "does not match current tree" in res.stdout


@pytest.mark.unit
def test_evidence_phase_mismatch(
    run_scanner: Runner,
    committed_sources: tuple[Path, str],
    tmp_path: Path,
) -> None:
    repo, commit = committed_sources
    manifest = tmp_path / "manifest.csv"
    _write_bound_manifest(manifest, repo, commit)
    decisions = _removed(tmp_path / "decisions.json")
    evidence = tmp_path / "evidence.json"
    _write_evidence(evidence, repo, "after")
    res = _invoke(run_scanner, repo, tmp_path, "before", manifest, decisions, evidence)
    assert res.returncode == 1
    assert "Evidence phase after does not match before" in res.stdout


@pytest.mark.unit
def test_scanner_constants_in_decisions(
    run_scanner: Runner,
    committed_sources: tuple[Path, str],
    tmp_path: Path,
) -> None:
    repo, commit = committed_sources
    manifest = tmp_path / "manifest.csv"
    _write_bound_manifest(manifest, repo, commit)
    decisions = tmp_path / "decisions.json"
    _write_json(decisions, [{**_removed_decision(), "literal": "verify_quality_move"}])
    evidence = tmp_path / "evidence.json"
    _write_evidence(evidence, repo, "before")
    res = _invoke(run_scanner, repo, tmp_path, "before", manifest, decisions, evidence)
    assert res.returncode == 1
    assert "Cannot exclude scanner constants" in res.stdout


@pytest.mark.unit
def test_blanket_exclude_in_decisions(
    run_scanner: Runner,
    committed_sources: tuple[Path, str],
    tmp_path: Path,
) -> None:
    repo, commit = committed_sources
    manifest = tmp_path / "manifest.csv"
    _write_bound_manifest(manifest, repo, commit)
    decisions = tmp_path / "decisions.json"
    _write_json(decisions, [{**_removed_decision(), "literal": "scripts"}])
    evidence = tmp_path / "evidence.json"
    _write_evidence(evidence, repo, "before")
    res = _invoke(run_scanner, repo, tmp_path, "before", manifest, decisions, evidence)
    assert res.returncode == 1
    assert "Blanket excludes of src or scripts are not allowed" in res.stdout


@pytest.mark.unit
def test_executable_old_imports_excepted(
    run_scanner: Runner,
    committed_sources: tuple[Path, str],
    tmp_path: Path,
) -> None:
    repo, commit = committed_sources
    manifest = tmp_path / "manifest.csv"
    _write_bound_manifest(manifest, repo, commit)
    decisions = tmp_path / "decisions.json"
    _write_json(
        decisions,
        [
            {
                **_removed_decision(),
                "literal": "bioetl",
                "exception_allowed": True,
                "executable_import": True,
            }
        ],
    )
    evidence = tmp_path / "evidence.json"
    _write_evidence(evidence, repo, "before")
    res = _invoke(run_scanner, repo, tmp_path, "before", manifest, decisions, evidence)
    assert res.returncode == 1
    assert "Executable old imports cannot be excepted" in res.stdout


@pytest.mark.unit
def test_expired_review_by(
    run_scanner: Runner,
    committed_sources: tuple[Path, str],
    tmp_path: Path,
) -> None:
    repo, commit = committed_sources
    manifest = tmp_path / "manifest.csv"
    _write_bound_manifest(manifest, repo, commit)
    decisions = tmp_path / "decisions.json"
    _write_json(decisions, [{**_removed_decision(), "review_by": "2000-01-01"}])
    evidence = tmp_path / "evidence.json"
    _write_evidence(evidence, repo, "before")
    res = _invoke(run_scanner, repo, tmp_path, "before", manifest, decisions, evidence)
    assert res.returncode == 1
    assert "Decision review_by is expired: 2000-01-01" in res.stdout


@pytest.mark.unit
def test_decisions_object_shape(
    run_scanner: Runner,
    committed_sources: tuple[Path, str],
    tmp_path: Path,
) -> None:
    repo, commit = committed_sources
    manifest = tmp_path / "manifest.csv"
    _write_bound_manifest(manifest, repo, commit)
    decisions = tmp_path / "decisions.json"
    _write_json(
        decisions, {"metadata": {"owner": "QM-01"}, "decisions": [_removed_decision()]}
    )
    evidence = tmp_path / "evidence.json"
    _write_evidence(evidence, repo, "before")
    res = _invoke(run_scanner, repo, tmp_path, "before", manifest, decisions, evidence)
    assert res.returncode == 0
    assert "Verification PASS" in res.stdout


@pytest.mark.unit
def test_decisions_object_missing_list(
    run_scanner: Runner,
    committed_sources: tuple[Path, str],
    tmp_path: Path,
) -> None:
    repo, commit = committed_sources
    manifest = tmp_path / "manifest.csv"
    _write_bound_manifest(manifest, repo, commit)
    decisions = tmp_path / "decisions.json"
    _write_json(decisions, {"metadata": {}})
    res = _invoke(
        run_scanner,
        repo,
        tmp_path,
        "before",
        manifest,
        decisions,
        tmp_path / "evidence.json",
    )
    assert res.returncode == 1
    assert "Decisions payload must be a list or an object with decisions" in res.stdout


@pytest.mark.unit
def test_valid_before(
    run_scanner: Runner,
    committed_sources: tuple[Path, str],
    tmp_path: Path,
) -> None:
    repo, commit = committed_sources
    manifest = tmp_path / "manifest.csv"
    _write_bound_manifest(manifest, repo, commit)
    decisions = _removed(tmp_path / "decisions.json")
    evidence = tmp_path / "evidence.json"
    _write_evidence(evidence, repo, "before")
    res = _invoke(run_scanner, repo, tmp_path, "before", manifest, decisions, evidence)
    assert callable(verify_quality_move_main)
    assert res.returncode == 0, res.stdout + res.stderr
    assert "Verification PASS" in res.stdout
    written = json.loads(
        (tmp_path / "out" / "execution_evidence.json").read_text(encoding="utf-8")
    )
    assert written["status"] == "PASS"
    assert written["phase"] == "before"
    assert written["dirty"] is False
    assert written["tree"] == _head_tree(repo)
    assert written["terminal_exit_code"] == 0
    assert written["interpreter"] == sys.executable
    assert (
        written["input_hashes"]["manifest"]
        == hashlib.sha256(manifest.read_bytes()).hexdigest()
    )
    assert (tmp_path / "out" / "verify.log").read_text(encoding="utf-8") == "PASS\n"


@pytest.mark.unit
def test_dirty_worktree(
    run_scanner: Runner,
    committed_sources: tuple[Path, str],
    tmp_path: Path,
) -> None:
    repo, commit = committed_sources
    manifest = tmp_path / "manifest.csv"
    _write_bound_manifest(manifest, repo, commit)
    decisions = _removed(tmp_path / "decisions.json")
    evidence = tmp_path / "evidence.json"
    _write_evidence(evidence, repo, "before")
    (repo / _source(0)).write_text("changed", encoding="utf-8")
    res = _invoke(run_scanner, repo, tmp_path, "before", manifest, decisions, evidence)
    assert res.returncode == 1
    assert "working tree is dirty" in res.stdout


@pytest.mark.unit
def test_valid_after(
    run_scanner: Runner,
    committed_sources: tuple[Path, str],
    tmp_path: Path,
) -> None:
    repo, commit = committed_sources
    _commit_move(repo)
    manifest = tmp_path / "manifest.csv"
    _write_bound_manifest(manifest, repo, commit)
    decisions = _removed(tmp_path / "decisions.json")
    evidence = tmp_path / "evidence.json"
    _write_evidence(evidence, repo, "after")
    res = _invoke(run_scanner, repo, tmp_path, "after", manifest, decisions, evidence)
    assert res.returncode == 0, res.stdout + res.stderr
    assert "Verification PASS" in res.stdout


@pytest.mark.unit
def test_after_source_still_exists(
    run_scanner: Runner,
    committed_sources: tuple[Path, str],
    tmp_path: Path,
) -> None:
    repo, commit = committed_sources
    _commit_move(repo, keep_source=True)
    manifest = tmp_path / "manifest.csv"
    _write_bound_manifest(manifest, repo, commit)
    decisions = _removed(tmp_path / "decisions.json")
    evidence = tmp_path / "evidence.json"
    _write_evidence(evidence, repo, "after")
    res = _invoke(run_scanner, repo, tmp_path, "after", manifest, decisions, evidence)
    assert res.returncode == 1
    assert "Phase after: source still exists" in res.stdout


@pytest.mark.unit
def test_after_leftover_import(
    run_scanner: Runner,
    committed_sources: tuple[Path, str],
    tmp_path: Path,
) -> None:
    repo, commit = committed_sources
    consumer = "scripts/consumer.py"
    _commit_move(repo, extra={consumer: "from bioetl.test0 import moved\n"})
    manifest = tmp_path / "manifest.csv"
    _write_bound_manifest(manifest, repo, commit)
    decisions = _removed(tmp_path / "decisions.json")
    evidence = tmp_path / "evidence.json"
    _write_evidence(evidence, repo, "after")
    res = _invoke(run_scanner, repo, tmp_path, "after", manifest, decisions, evidence)
    assert res.returncode == 1
    assert (
        "Phase after: leftover import bioetl.test0 in scripts/consumer.py" in res.stdout
    )


@pytest.mark.unit
def test_after_leftover_import_exempt(
    run_scanner: Runner,
    committed_sources: tuple[Path, str],
    tmp_path: Path,
) -> None:
    repo, commit = committed_sources
    consumer = "scripts/consumer.py"
    text = "from bioetl.test0 import moved\n"
    _commit_move(repo, extra={consumer: text})
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    manifest = tmp_path / "manifest.csv"
    _write_bound_manifest(manifest, repo, commit)
    decisions = tmp_path / "decisions.json"
    _write_json(
        decisions,
        [
            {
                "path": consumer,
                "literal": "bioetl.test0",
                "context": "import",
                "purpose": "reviewed shim",
                "owner": "QM-03",
                "reviewed_content_sha256": digest,
                "review_by": "QM-02",
                "exception_allowed": True,
                "executable_import": False,
            }
        ],
    )
    evidence = tmp_path / "evidence.json"
    _write_evidence(evidence, repo, "after")
    res = _invoke(run_scanner, repo, tmp_path, "after", manifest, decisions, evidence)
    assert res.returncode == 0, res.stdout + res.stderr
    assert "Verification PASS" in res.stdout


@pytest.mark.unit
def test_outdated_addressable_decision(
    run_scanner: Runner,
    committed_sources: tuple[Path, str],
    tmp_path: Path,
) -> None:
    repo, commit = committed_sources
    manifest = tmp_path / "manifest.csv"
    _write_bound_manifest(manifest, repo, commit)
    (repo / "test.py").write_text("hello", encoding="utf-8")
    decisions = tmp_path / "decisions.json"
    _write_json(
        decisions,
        [
            {
                "path": "test.py",
                "literal": "bioetl.foo",
                "context": "import",
                "purpose": "test",
                "owner": "QM-03",
                "reviewed_content_sha256": "z",
                "review_by": "QM-01",
            }
        ],
    )
    res = _invoke(
        run_scanner,
        repo,
        tmp_path,
        "before",
        manifest,
        decisions,
        tmp_path / "evidence.json",
    )
    assert res.returncode == 1
    assert "Hash mismatch" in res.stdout


@pytest.mark.unit
def test_invalid_review_by_date(
    run_scanner: Runner,
    committed_sources: tuple[Path, str],
    tmp_path: Path,
) -> None:
    repo, commit = committed_sources
    manifest = tmp_path / "manifest.csv"
    _write_bound_manifest(manifest, repo, commit)
    decisions = tmp_path / "decisions.json"
    _write_json(decisions, [{**_removed_decision(), "review_by": "2026-13-45"}])
    evidence = tmp_path / "evidence.json"
    _write_evidence(evidence, repo, "before")
    res = _invoke(run_scanner, repo, tmp_path, "before", manifest, decisions, evidence)
    assert res.returncode == 1
    assert "Decision review_by is not a valid date: 2026-13-45" in res.stdout
    assert (tmp_path / "out" / "execution_evidence.json").is_file()


@pytest.mark.unit
def test_after_from_import_name(
    run_scanner: Runner,
    committed_sources: tuple[Path, str],
    tmp_path: Path,
) -> None:
    repo, commit = committed_sources
    _commit_move(repo, extra={"scripts/consumer.py": "from bioetl import test0\n"})
    manifest = tmp_path / "manifest.csv"
    _write_bound_manifest(manifest, repo, commit)
    decisions = _removed(tmp_path / "decisions.json")
    evidence = tmp_path / "evidence.json"
    _write_evidence(evidence, repo, "after")
    res = _invoke(run_scanner, repo, tmp_path, "after", manifest, decisions, evidence)
    assert res.returncode == 1
    assert (
        "Phase after: leftover import bioetl.test0 in scripts/consumer.py" in res.stdout
    )


@pytest.mark.unit
def test_after_target_keeps_old_import(
    run_scanner: Runner,
    committed_sources: tuple[Path, str],
    tmp_path: Path,
) -> None:
    repo, commit = committed_sources
    target = _target(0)
    _commit_move(repo, extra={target: "from bioetl import test0\n"})
    manifest = tmp_path / "manifest.csv"
    _write_bound_manifest(manifest, repo, commit)
    decisions = _removed(tmp_path / "decisions.json")
    evidence = tmp_path / "evidence.json"
    _write_evidence(evidence, repo, "after")
    res = _invoke(run_scanner, repo, tmp_path, "after", manifest, decisions, evidence)
    assert res.returncode == 1
    assert f"Phase after: leftover import bioetl.test0 in {target}" in res.stdout


@pytest.mark.unit
def test_after_unparseable_python(
    run_scanner: Runner,
    committed_sources: tuple[Path, str],
    tmp_path: Path,
) -> None:
    repo, commit = committed_sources
    _commit_move(repo, extra={"scripts/broken.py": "def (\n"})
    manifest = tmp_path / "manifest.csv"
    _write_bound_manifest(manifest, repo, commit)
    decisions = _removed(tmp_path / "decisions.json")
    evidence = tmp_path / "evidence.json"
    _write_evidence(evidence, repo, "after")
    res = _invoke(run_scanner, repo, tmp_path, "after", manifest, decisions, evidence)
    assert res.returncode == 1
    assert "Could not parse Python file scripts/broken.py" in res.stdout
