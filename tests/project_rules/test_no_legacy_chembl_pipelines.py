from pathlib import Path


def test_legacy_chembl_pipeline_modules_absent() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    legacy_files = [
        repo_root / "src/bioetl/pipelines/chembl/thin.py",
        repo_root / "src/bioetl/pipelines/chembl/base.py",
    ]

    for path in legacy_files:
        assert not path.exists(), f"Legacy module should be removed: {path}"

    legacy_run_files = list(
        (repo_root / "src/bioetl/pipelines/chembl").glob("**/run.py")
    )
    assert not legacy_run_files, "Legacy run.py modules should be removed"
