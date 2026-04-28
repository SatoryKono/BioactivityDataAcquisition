"""Regression checks for project Codex launcher scripts."""

from __future__ import annotations

from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_wsl_launchers_use_local_bootstrap_helper() -> None:
    """Bash launchers should resolve Codex through the repo-local helper."""
    root = _project_root()
    codex_sh = (
        root / "scripts" / "ops" / "launchers" / "codex" / "codex.sh"
    ).read_text(encoding="utf-8")
    codex_exec_sh = (
        root / "scripts" / "ops" / "launchers" / "codex" / "codex-exec.sh"
    ).read_text(encoding="utf-8")

    assert "ensure-codex-cli.sh" in codex_sh
    assert 'exec "${CODEX_BIN}" -C "${REPO_ROOT}"' in codex_sh
    assert "npm install -g @openai/codex" not in codex_sh

    assert "ensure-codex-cli.sh" in codex_exec_sh
    assert 'exec "${CODEX_BIN}" exec --full-auto -C "${REPO_ROOT}" "$@"' in (
        codex_exec_sh
    )
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
    assert 'bash "%REPO_WSL%/scripts/ops/launchers/codex/codex.sh"' in codex_bat
    assert "wslpath -a" in codex_bat

    assert "/dev/null" not in codex_exec_bat
    assert (
        'bash "%REPO_WSL%/scripts/ops/launchers/codex/codex-exec.sh"' in codex_exec_bat
    )
    assert "wslpath -a" in codex_exec_bat


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


def test_powershell_codex_launcher_is_thin_transport_to_canonical_wsl_entrypoint() -> (
    None
):
    """PowerShell launcher must delegate to the canonical WSL/Bash entrypoint."""
    root = _project_root()
    launcher_ps1 = (root / "scripts" / "ai" / "codex" / "run-codex.ps1").read_text(
        encoding="utf-8"
    )

    assert "run-codex.sh" in launcher_ps1
    assert "wsl -d $WslDistro -e bash -- $LauncherWSL" in launcher_ps1
    assert "npm install -g @openai/codex" not in launcher_ps1
