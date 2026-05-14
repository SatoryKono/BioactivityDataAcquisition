"""Architecture guardrails for pytest bootstrap import-path handling."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP_FILES = (
    ROOT / "conftest.py",
    ROOT / "tests" / "conftest.py",
)
FORBIDDEN_IMPORT_PATH_MUTATIONS = (
    "sys.path.insert",
    "sys.path.append",
    "sys.path.extend",
    "site.addsitedir",
)


def test_pytest_bootstrap_does_not_mutate_import_path() -> None:
    """Pytest bootstrap must rely on canonical config, not runtime path surgery."""
    offenders: list[str] = []
    for bootstrap_file in BOOTSTRAP_FILES:
        content = bootstrap_file.read_text(encoding="utf-8")
        for token in FORBIDDEN_IMPORT_PATH_MUTATIONS:
            if token in content:
                offenders.append(f"{bootstrap_file.relative_to(ROOT)}: {token}")

    assert not offenders, (
        "Remove pytest bootstrap import-path mutations; rely on "
        "pyproject.toml [tool.pytest.ini_options]. Offenders:\n"
        + "\n".join(f"  - {offender}" for offender in offenders)
    )
