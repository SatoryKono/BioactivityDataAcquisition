# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Regression checks for project Codex launcher scripts."""

from __future__ import annotations

import pytest

from pathlib import Path


pytestmark = pytest.mark.architecture


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_wsl_launchers_use_local_bootstrap_helper() -> None:
    """Bash launchers should redirect to canonical launcher with deprecation warning."""
    root = _project_root()
    codex_sh = (
        root / "scripts" / "ops" / "launchers" / "codex" / "codex.sh"
    ).read_text(encoding="utf-8")
    codex_exec_sh = (
        root / "scripts" / "ops" / "launchers" / "codex" / "codex-exec.sh"
    ).read_text(encoding="utf-8")

    # Check that ops launchers are deprecated wrappers
    assert "DEPRECATED" in codex_sh
    assert "canonical" in codex_sh.lower()
    assert "scripts/ai/codex/run-codex.sh" in codex_sh
    assert "exec bash" in codex_sh
    assert "ensure-codex-cli.sh" not in codex_sh  # No longer uses bootstrap helper

    assert "DEPRECATED" in codex_exec_sh
    assert "canonical" in codex_exec_sh.lower()
    assert "scripts/ai/codex/run-codex.sh" in codex_exec_sh
    assert "exec bash" in codex_exec_sh
    assert "ensure-codex-cli.sh" not in codex_exec_sh  # No longer uses bootstrap helper
    assert "npm install -g @openai/codex" not in codex_exec_sh


def test_windows_launchers_delegate_to_wsl_scripts_without_posix_redirects() -> None:
    """Batch launchers should delegate to bash wrappers and avoid `/dev/null`."""
    root = _project_root()
    codex_bat = (
        root / "scripts" / "ops" / "launchers" / "codex" / "codex.bat"
    ).read_text(encoding="utf-8")
    codex_exec_bat = (
        root / "scripts" / "ops" / "launchers" / "codex" / "codex-exec.bat"
    ).read_text(encoding="utf-8")

    assert "/dev/null" not in codex_bat
    assert 'bash -i "%REPO_WSL%/scripts/ai/codex/run-codex.sh"' in codex_bat
    assert "wslpath -a" in codex_bat

    assert "/dev/null" not in codex_exec_bat
    assert 'bash "%REPO_WSL%/scripts/ai/codex/run-codex.sh"' in codex_exec_bat
    assert 'bash -i "%REPO_WSL%/scripts/ai/codex/run-codex.sh"' not in (codex_exec_bat)
    assert "wslpath -a" in codex_exec_bat


def test_windows_compatibility_wrappers_delegate_to_existing_targets() -> None:
    """Compatibility wrappers should delegate only to live launcher targets."""
    root = _project_root()
    codex_wsl_bat = (
        root / "scripts" / "ops" / "launchers" / "codex" / "codex-wsl.bat"
    ).read_text(encoding="utf-8")
    start_codex_bat = (
        root / "scripts" / "ops" / "launchers" / "codex" / "start-codex.bat"
    ).read_text(encoding="utf-8")
    verify_setup_bat = (
        root / "scripts" / "ops" / "launchers" / "codex" / "verify-setup.bat"
    ).read_text(encoding="utf-8")
    verify_setup_ps1 = (
        root / "scripts" / "ops" / "launchers" / "codex" / "verify-setup.ps1"
    ).read_text(encoding="utf-8")

    assert "launch.bat" not in codex_wsl_bat
    assert 'call "%~dp0codex.bat" %*' in codex_wsl_bat

    assert "launch.bat" not in start_codex_bat
    assert 'call "%~dp0codex.bat" %*' in start_codex_bat

    assert "verify_setup.bat" not in verify_setup_bat
    assert (
        'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0verify-setup.ps1" %*'
        in verify_setup_bat
    )

    assert "verify_setup.ps1" not in verify_setup_ps1
    assert "run-codex.ps1" in verify_setup_ps1
    assert "& $Target check" in verify_setup_ps1


def test_wsl_setup_uses_local_update_path() -> None:
    """Setup and verification scripts should rely on the repo-local installer."""
    root = _project_root()
    setup_sh = (
        root / "scripts" / "ai" / "codex" / "helper" / "setup-wsl.sh"
    ).read_text(encoding="utf-8")
    verify_sh = (
        root / "scripts" / "ai" / "codex" / "helper" / "verify-setup.sh"
    ).read_text(encoding="utf-8")

    assert "ensure-codex-cli.sh" in setup_sh
    assert "--update" in setup_sh
    assert "npm install -g @openai/codex" not in setup_sh

    assert "ensure-codex-cli.sh" in verify_sh
    assert "--no-install --print-bin" in verify_sh


def test_removed_thin_wrappers_are_absent_and_router_uses_canonical_targets() -> None:
    """Thin wrappers should be gone once the router dispatches canonical targets."""
    root = _project_root()
    ops_router = (root / "scripts" / "ops" / "__main__.py").read_text(encoding="utf-8")

    assert not (
        root / "scripts" / "ops" / "launchers" / "codex" / "codex-headless.sh"
    ).exists()
    assert not (
        root / "scripts" / "ops" / "launchers" / "codex" / "diagnose-codex-wsl.sh"
    ).exists()
    assert "../ai/codex/headless.sh" in ops_router
    assert "../ai/codex/diagnose_wsl.sh" in ops_router
    assert (root / "scripts" / "ai" / "codex" / "headless.sh").exists()
    assert (root / "scripts" / "ai" / "codex" / "headless.ps1").exists()
    assert (root / "scripts" / "ai" / "codex" / "diagnose_wsl.sh").exists()
    assert (root / "scripts" / "ai" / "codex" / "diagnose_wsl.ps1").exists()
    assert (root / "scripts" / "ai" / "codex" / "diagnose_wsl.bat").exists()


def test_canonical_launcher_exposes_diagnostics_and_baseline_modes() -> None:
    root = _project_root()
    launcher = (root / "scripts" / "ai" / "codex" / "run-codex.sh").read_text(
        encoding="utf-8"
    )
    readme = (root / "scripts" / "ai" / "codex" / "README.md").read_text(
        encoding="utf-8"
    )

    assert 'python3 "${SCRIPT_DIR}/efficiency_baseline.py"' in launcher
    assert 'bash "${SCRIPT_DIR}/diagnose_wsl.sh"' in launcher
    assert "## Canonical launch modes" in readme
    assert "Fast/headless" in readme


def test_canonical_launcher_enforces_private_defaults_and_managed_path() -> None:
    root = _project_root()
    launcher = (root / "scripts/ai/codex/run-codex.sh").read_text(encoding="utf-8")
    headless = (root / "scripts/ai/codex/headless.sh").read_text(encoding="utf-8")

    assert "umask 077" in launcher
    assert "umask 077" in headless
    assert launcher.index('PATH="${USER_NPM_BIN}:${PATH}"') < launcher.index(
        'PATH="${LINUX_NPM_BIN}:${PATH}"'
    )
    assert 'local_state_audit.py" audit' in launcher


def test_environment_check_invokes_tracked_non_executable_helpers_via_bash() -> None:
    root = _project_root()
    helper = (root / "scripts/ai/codex/helper/check-env.sh").read_text(encoding="utf-8")

    assert '[[ -f "${ENSURE_SCRIPT}" ]]' in helper
    assert 'timeout 10 bash "${ENSURE_SCRIPT}"' in helper
    assert '[[ -f "${ENSURE_MCP_SCRIPT}" ]]' in helper
    assert 'timeout 30 bash "${ENSURE_MCP_SCRIPT}"' in helper
    assert "bash -c" not in helper


def test_powershell_codex_launcher_is_thin_transport_to_canonical_wsl_entrypoint() -> (
    None
):
    """PowerShell launcher must delegate to the canonical WSL/Bash entrypoint."""
    root = _project_root()
    launcher_ps1 = (root / "scripts" / "ai" / "codex" / "run-codex.ps1").read_text(
        encoding="utf-8"
    )

    assert "run-codex.sh" in launcher_ps1
    assert "Invoke-CodexInWsl" in launcher_ps1
    assert "& $wslExe -d $wslDistro -e bash -- $LauncherWSL" in launcher_ps1
    assert "& $wslExe -e bash -- $LauncherWSL" in launcher_ps1
    assert "npm install -g @openai/codex" not in launcher_ps1
