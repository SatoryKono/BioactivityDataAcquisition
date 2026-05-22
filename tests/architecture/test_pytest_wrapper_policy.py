"""Architecture tests for local pytest wrapper policy invariants."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUN_PYTEST_SH = ROOT / "scripts" / "engineering" / "dev" / "run_pytest.sh"
RUN_PYTEST_PS1 = ROOT / "scripts" / "engineering" / "dev" / "run_pytest.ps1"


def test_shell_wrapper_keeps_local_coverage_opt_in() -> None:
    content = RUN_PYTEST_SH.read_text(encoding="utf-8")

    assert 'PYTEST_WITH_COVERAGE="${BIOETL_PYTEST_WITH_COVERAGE:-0}"' in content
    assert 'if [[ "$arg" == "--with-coverage" ]]; then' in content
    assert "DEFAULT_FLAGS=(-q --maxfail=1)" in content
    assert (
        'DEFAULT_FLAGS=(--cov=src/bioetl --cov-report=term "${DEFAULT_FLAGS[@]}")'
        in content
    )


def test_powershell_wrapper_keeps_local_coverage_opt_in() -> None:
    content = RUN_PYTEST_PS1.read_text(encoding="utf-8")

    assert '$PytestWithCoverage = $env:BIOETL_PYTEST_WITH_COVERAGE -eq "1"' in content
    assert 'if ($Arg -eq "--with-coverage") {' in content
    assert '$PytestArgs = @("-q", "--maxfail=1") + $PytestArgs' in content
    assert (
        '$PytestArgs = @("--cov=src/bioetl", "--cov-report=term") + $PytestArgs'
        in content
    )


def test_wrappers_allow_no_cov_override_without_loading_coverage_flags() -> None:
    shell = RUN_PYTEST_SH.read_text(encoding="utf-8")
    powershell = RUN_PYTEST_PS1.read_text(encoding="utf-8")

    assert 'if [[ "$arg" == "--no-cov" ]]; then' in shell
    assert 'if [[ "$PYTEST_WITH_COVERAGE" == "1" && "$PYTEST_NO_COV" != "1"' in shell
    assert (
        "--cov|--cov=*|--cov-report|--cov-report=*|--cov-config|--cov-config=*)"
        in shell
    )

    assert 'if ($Arg -eq "--no-cov") {' in powershell
    assert "if ($PytestWithCoverage -and -not $PytestNoCov) {" in powershell
    assert "$PytestArgs = Remove-CoverageArgs -Args $PytestArgs" in powershell


def test_wrapper_autopreflight_scope_is_limited_to_full_repo_and_config_heavy_runs() -> (
    None
):
    shell = RUN_PYTEST_SH.read_text(encoding="utf-8")
    powershell = RUN_PYTEST_PS1.read_text(encoding="utf-8")
    shell_scope_block = shell[
        shell.index("should_run_preflight()") : shell.index(
            "determine_preflight_scope()"
        )
    ]
    powershell_scope_block = powershell[
        powershell.index("function Test-PreflightScope") : powershell.index(
            "foreach ($Arg in $PytestArgs)"
        )
    ]

    for expected in (
        "tests/architecture",
        "tests/integration/config",
        "tests/integration/ci",
    ):
        assert expected in shell_scope_block
        assert (
            expected in powershell_scope_block
            or expected.replace("/", "\\") in powershell_scope_block
        )

    for unexpected in (
        "tests/e2e",
        "tests/contract",
        "tests/smoke",
    ):
        assert unexpected not in shell_scope_block
        assert unexpected not in powershell_scope_block
