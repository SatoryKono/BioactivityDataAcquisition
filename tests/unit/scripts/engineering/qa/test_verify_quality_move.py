import json
import os
import subprocess
from pathlib import Path
from collections.abc import Generator

import pytest


@pytest.fixture
def run_scanner(tmp_path: Path) -> callable:
    def _run_scanner(
        phase: str,
        manifest_path: str,
        decisions_path: str,
        evidence_path: str,
        repo: str,
        out_dir: str,
    ) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(
            Path(__file__).parent.parent.parent.parent.parent.parent
        )
        return subprocess.run(
            [
                "python",
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
        )

    return _run_scanner


@pytest.fixture
def synthetic_repo(tmp_path: Path) -> Generator[Path, None, None]:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=repo, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
    yield repo


@pytest.fixture
def valid_decisions(tmp_path: Path) -> Path:
    p = tmp_path / "decisions.json"
    p.write_text(
        json.dumps(
            [
                {
                    "path": "tests/test_x.py",
                    "literal": "bioetl.foo",
                    "context": "import",
                    "purpose": "test",
                    "owner": "QM-03",
                    "reviewed_content_sha256": "x",
                    "review_by": "QM-01",
                }
            ]
        )
    )
    return p


@pytest.fixture
def evidence_for_tree(tmp_path: Path, synthetic_repo: Path) -> Path:
    # Need to commit something to get a real tree
    (synthetic_repo / "dummy.txt").write_text("hello")
    subprocess.run(["git", "add", "dummy.txt"], cwd=synthetic_repo, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=synthetic_repo, check=True)
    tree_out = subprocess.run(
        ["git", "rev-parse", "HEAD^{tree}"],
        cwd=synthetic_repo,
        check=True,
        capture_output=True,
        text=True,
    )
    tree = tree_out.stdout.strip()

    p = tmp_path / "evidence.json"
    p.write_text(json.dumps({"status": "PASS", "tree": tree}))
    return p


def create_manifest(
    path: Path,
    rows: int = 30,
    valid: bool = True,
    dup_source: bool = False,
    dup_target: bool = False,
    invalid_cols: bool = False,
    bad_prefix: bool = False,
) -> None:
    header = "source_path,target_path,blob_sha,base_commit,snapshot_relation_prior,evidence_status,required_changes,acceptance\n"
    if invalid_cols:
        header = "source_path,target_path,blob_sha\n"

    lines = [header]
    for i in range(rows):
        src = f"src/bioetl/test{i}.py"
        tgt = f"scripts/engineering/qa/test{i}.py"
        if bad_prefix:
            src = f"bioetl/test{i}.py"

        if dup_source and i == 1:
            src = "src/bioetl/test0.py"
        if dup_target and i == 1:
            tgt = "scripts/engineering/qa/test0.py"

        lines.append(f"{src},{tgt},sha,base,rel,status,changes,acc\n")

    path.write_text("".join(lines))


def setup_files(repo: Path, before: bool = True) -> None:
    for i in range(30):
        if before:
            p = repo / f"src/bioetl/test{i}.py"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("code")
        else:
            p = repo / f"scripts/engineering/qa/test{i}.py"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("code")


@pytest.mark.unit
def test_missing_evidence(run_scanner, synthetic_repo, valid_decisions, tmp_path):
    manifest = tmp_path / "manifest.csv"
    create_manifest(manifest)
    out_dir = tmp_path / "out"

    res = run_scanner(
        "before",
        str(manifest),
        str(valid_decisions),
        str(tmp_path / "missing.json"),
        str(synthetic_repo),
        str(out_dir),
    )
    assert res.returncode == 1
    assert "Missing evidence path" in res.stdout

    ev_path = out_dir / "execution_evidence.json"
    assert ev_path.exists()
    ev_data = json.loads(ev_path.read_text())
    assert ev_data["status"] == "NOT_RUN"


@pytest.mark.unit
def test_invalid_csv_schema(
    run_scanner, synthetic_repo, valid_decisions, evidence_for_tree, tmp_path
):
    manifest = tmp_path / "manifest.csv"
    create_manifest(manifest, invalid_cols=True)
    out_dir = tmp_path / "out"

    res = run_scanner(
        "before",
        str(manifest),
        str(valid_decisions),
        str(evidence_for_tree),
        str(synthetic_repo),
        str(out_dir),
    )
    assert res.returncode == 1
    assert "Manifest Error: Missing columns" in res.stdout

    ev_data = json.loads((out_dir / "execution_evidence.json").read_text())
    assert ev_data["status"] == "BLOCKED"


@pytest.mark.unit
def test_wrong_row_count(
    run_scanner, synthetic_repo, valid_decisions, evidence_for_tree, tmp_path
):
    manifest = tmp_path / "manifest.csv"
    create_manifest(manifest, rows=29)
    out_dir = tmp_path / "out"

    res = run_scanner(
        "before",
        str(manifest),
        str(valid_decisions),
        str(evidence_for_tree),
        str(synthetic_repo),
        str(out_dir),
    )
    assert res.returncode == 1
    assert "Expected exactly 30 rows" in res.stdout


@pytest.mark.unit
def test_duplicate_source(
    run_scanner, synthetic_repo, valid_decisions, evidence_for_tree, tmp_path
):
    manifest = tmp_path / "manifest.csv"
    create_manifest(manifest, dup_source=True)
    out_dir = tmp_path / "out"

    res = run_scanner(
        "before",
        str(manifest),
        str(valid_decisions),
        str(evidence_for_tree),
        str(synthetic_repo),
        str(out_dir),
    )
    assert res.returncode == 1
    assert "Duplicate source_path" in res.stdout


@pytest.mark.unit
def test_duplicate_target(
    run_scanner, synthetic_repo, valid_decisions, evidence_for_tree, tmp_path
):
    manifest = tmp_path / "manifest.csv"
    create_manifest(manifest, dup_target=True)
    out_dir = tmp_path / "out"

    res = run_scanner(
        "before",
        str(manifest),
        str(valid_decisions),
        str(evidence_for_tree),
        str(synthetic_repo),
        str(out_dir),
    )
    assert res.returncode == 1
    assert "Duplicate target_path" in res.stdout


@pytest.mark.unit
def test_wrong_evidence_tree(
    run_scanner, synthetic_repo, valid_decisions, evidence_for_tree, tmp_path
):
    manifest = tmp_path / "manifest.csv"
    create_manifest(manifest)
    out_dir = tmp_path / "out"

    # modify tree
    (synthetic_repo / "other.txt").write_text("hey")
    subprocess.run(["git", "add", "other.txt"], cwd=synthetic_repo, check=True)
    subprocess.run(["git", "commit", "-m", "update"], cwd=synthetic_repo, check=True)

    res = run_scanner(
        "before",
        str(manifest),
        str(valid_decisions),
        str(evidence_for_tree),
        str(synthetic_repo),
        str(out_dir),
    )
    assert res.returncode == 1
    assert "does not match current tree" in res.stdout


@pytest.mark.unit
def test_scanner_constants_in_decisions(
    run_scanner, synthetic_repo, evidence_for_tree, tmp_path
):
    manifest = tmp_path / "manifest.csv"
    create_manifest(manifest)
    out_dir = tmp_path / "out"

    decisions = tmp_path / "decisions.json"
    decisions.write_text(
        json.dumps(
            [
                {
                    "path": "test.py",
                    "literal": "verify_quality_move",
                    "context": "x",
                    "purpose": "y",
                    "owner": "QM-03",
                    "reviewed_content_sha256": "z",
                    "review_by": "w",
                }
            ]
        )
    )

    res = run_scanner(
        "before",
        str(manifest),
        str(decisions),
        str(evidence_for_tree),
        str(synthetic_repo),
        str(out_dir),
    )
    assert res.returncode == 1
    assert "Cannot exclude scanner constants" in res.stdout


@pytest.mark.unit
def test_blanket_exclude_in_decisions(
    run_scanner, synthetic_repo, evidence_for_tree, tmp_path
):
    manifest = tmp_path / "manifest.csv"
    create_manifest(manifest)
    out_dir = tmp_path / "out"

    decisions = tmp_path / "decisions.json"
    decisions.write_text(
        json.dumps(
            [
                {
                    "path": "test.py",
                    "literal": "scripts",
                    "context": "x",
                    "purpose": "y",
                    "owner": "QM-03",
                    "reviewed_content_sha256": "z",
                    "review_by": "w",
                }
            ]
        )
    )

    res = run_scanner(
        "before",
        str(manifest),
        str(decisions),
        str(evidence_for_tree),
        str(synthetic_repo),
        str(out_dir),
    )
    assert res.returncode == 1
    assert "Blanket excludes of src or scripts are not allowed" in res.stdout


@pytest.mark.unit
def test_executable_old_imports_excepted(
    run_scanner, synthetic_repo, evidence_for_tree, tmp_path
):
    manifest = tmp_path / "manifest.csv"
    create_manifest(manifest)
    out_dir = tmp_path / "out"

    decisions = tmp_path / "decisions.json"
    decisions.write_text(
        json.dumps(
            [
                {
                    "path": "test.py",
                    "literal": "bioetl",
                    "context": "x",
                    "purpose": "y",
                    "owner": "QM-03",
                    "reviewed_content_sha256": "z",
                    "review_by": "w",
                    "exception_allowed": True,
                    "executable_import": True,
                }
            ]
        )
    )

    res = run_scanner(
        "before",
        str(manifest),
        str(decisions),
        str(evidence_for_tree),
        str(synthetic_repo),
        str(out_dir),
    )
    assert res.returncode == 1
    assert "Executable old imports cannot be excepted" in res.stdout


@pytest.mark.unit
def test_valid_before(
    run_scanner, synthetic_repo, valid_decisions, evidence_for_tree, tmp_path
):
    manifest = tmp_path / "manifest.csv"
    create_manifest(manifest)
    out_dir = tmp_path / "out"

    setup_files(synthetic_repo, before=True)

    res = run_scanner(
        "before",
        str(manifest),
        str(valid_decisions),
        str(evidence_for_tree),
        str(synthetic_repo),
        str(out_dir),
    )
    assert res.returncode == 0
    assert "Verification PASS" in res.stdout


@pytest.mark.unit
def test_valid_after(
    run_scanner, synthetic_repo, valid_decisions, evidence_for_tree, tmp_path
):
    manifest = tmp_path / "manifest.csv"
    create_manifest(manifest)
    out_dir = tmp_path / "out"

    setup_files(synthetic_repo, before=False)

    res = run_scanner(
        "after",
        str(manifest),
        str(valid_decisions),
        str(evidence_for_tree),
        str(synthetic_repo),
        str(out_dir),
    )
    assert res.returncode == 0
    assert "Verification PASS" in res.stdout


@pytest.mark.unit
def test_after_source_still_exists(
    run_scanner, synthetic_repo, valid_decisions, evidence_for_tree, tmp_path
):
    manifest = tmp_path / "manifest.csv"
    create_manifest(manifest)
    out_dir = tmp_path / "out"

    setup_files(synthetic_repo, before=False)
    # manually create one source
    p = synthetic_repo / "src/bioetl/test0.py"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("x")

    res = run_scanner(
        "after",
        str(manifest),
        str(valid_decisions),
        str(evidence_for_tree),
        str(synthetic_repo),
        str(out_dir),
    )
    assert res.returncode == 1
    assert "Phase after: source still exists" in res.stdout


@pytest.mark.unit
def test_outdated_addressable_decision(
    run_scanner, synthetic_repo, evidence_for_tree, tmp_path
):
    manifest = tmp_path / "manifest.csv"
    create_manifest(manifest)
    out_dir = tmp_path / "out"

    decisions = tmp_path / "decisions.json"
    decisions.write_text(
        json.dumps(
            [
                {
                    "path": "test.py",
                    "literal": "bioetl.foo",
                    "context": "import",
                    "purpose": "test",
                    "owner": "QM-03",
                    "reviewed_content_sha256": "z",
                    "review_by": "w",
                }
            ]
        )
    )

    p = synthetic_repo / "test.py"
    p.write_text("hello")
    # this will hash to something other than "z"

    res = run_scanner(
        "before",
        str(manifest),
        str(decisions),
        str(evidence_for_tree),
        str(synthetic_repo),
        str(out_dir),
    )
    assert res.returncode == 1
    assert "Hash mismatch" in res.stdout
