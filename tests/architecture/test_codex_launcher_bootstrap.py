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

import os
import shutil
import subprocess
import sys

import pytest

from pathlib import Path


pytestmark = pytest.mark.architecture

_BASH_SUBPROCESS_UNSUPPORTED_ON_WINDOWS = pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="bash-based Codex shim installers are not reliable on native Windows shells",
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _fake_codex_prefix(tmp_path: Path) -> Path:
    prefix = tmp_path / "managed"
    fake_codex = prefix / "bin" / "codex"
    fake_codex.parent.mkdir(parents=True)
    fake_codex.write_text(
        "#!/usr/bin/env bash\n"
        'if [[ -n "${REF_TOOL_API_KEY:-}" ]]; then echo ref_key=set; '
        "else echo ref_key=missing; fi\n"
        "printf 'arg=%s\\n' \"$@\"\n",
        encoding="utf-8",
    )
    fake_codex.chmod(0o700)
    return prefix


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
    complete_setup_sh = (
        root / "scripts" / "ai" / "codex" / "helper" / "setup-wsl-complete.sh"
    ).read_text(encoding="utf-8")
    verify_sh = (
        root / "scripts" / "ai" / "codex" / "helper" / "verify-setup.sh"
    ).read_text(encoding="utf-8")

    assert "ensure-codex-cli.sh" in setup_sh
    assert "--update" in setup_sh
    assert "--install-command-shim" in setup_sh
    assert "npm install -g @openai/codex" not in setup_sh

    assert "--install-command-shim" in complete_setup_sh

    assert "ensure-codex-cli.sh" in verify_sh
    assert "--no-install --print-bin" in verify_sh


def test_setup_installs_managed_direct_codex_command() -> None:
    """Canonical setup should install the PATH shim that loads Ref auth."""
    root = _project_root()
    setup_helper = (
        root / "scripts" / "ai" / "codex" / "helper" / "setup-env.sh"
    ).read_text(encoding="utf-8")
    ensure_helper = (
        root / "scripts" / "ai" / "codex" / "helper" / "ensure-codex-cli.sh"
    ).read_text(encoding="utf-8")

    assert '"${ENSURE_SCRIPT}" --install-command-shim' in setup_helper
    assert "--install-command-shim" in ensure_helper
    assert "BIOETL_CODEX_COMMAND_SHIM_DIR" in ensure_helper
    assert "run-codex-impl.sh" in ensure_helper


@_BASH_SUBPROCESS_UNSUPPORTED_ON_WINDOWS
def test_direct_codex_command_installer_is_bounded_and_secret_free(
    tmp_path: Path,
) -> None:
    """The local PATH shim delegates without copying credentials."""
    root = _project_root()
    ensure_helper = root / "scripts" / "ai" / "codex" / "helper" / "ensure-codex-cli.sh"
    shim_dir = tmp_path / "bin"
    fake_prefix = _fake_codex_prefix(tmp_path)
    env = {
        **os.environ,
        "BIOETL_CODEX_COMMAND_SHIM_DIR": str(shim_dir),
        "CODEX_NPM_PREFIX": str(fake_prefix),
    }

    completed = subprocess.run(
        ["bash", str(ensure_helper), "--install-command-shim"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )

    assert completed.returncode == 0, completed.stderr
    shim = shim_dir / "codex"
    content = shim.read_text(encoding="utf-8")
    assert "Managed by BioETL Codex launcher setup" in content
    assert "scripts/ai/codex/helper/run-codex-impl.sh" in content
    assert "REPO_ROOT=" in content
    assert '"$@"' in content
    assert "REF_TOOL_API_KEY" not in content

    original_stat = shim.stat()
    shim_dir.chmod(0o500)
    try:
        repeated = subprocess.run(
            ["bash", str(ensure_helper), "--install-command-shim"],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    finally:
        shim_dir.chmod(0o700)
    assert repeated.returncode == 0, repeated.stderr
    repeated_stat = shim.stat()
    assert repeated_stat.st_ino == original_stat.st_ino
    assert repeated_stat.st_mtime_ns == original_stat.st_mtime_ns

    direct_env = {
        **env,
        "CODEX_SKIP_MCP_SETUP": "1",
        "REF_TOOL_API_KEY": "synthetic-ref-key",
    }
    direct = subprocess.run(
        [str(shim), "mcp", "get", "ref"],
        cwd=root,
        env=direct_env,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert direct.returncode == 0, direct.stderr
    assert direct.stdout.splitlines() == [
        "ref_key=set",
        "arg=mcp",
        "arg=get",
        "arg=ref",
    ]


@_BASH_SUBPROCESS_UNSUPPORTED_ON_WINDOWS
def test_direct_codex_command_ensures_mcp_before_exec(tmp_path: Path) -> None:
    """The PATH shim must reconcile the shared MCP plane before Codex starts."""
    root = _project_root()
    source_helper_dir = root / "scripts" / "ai" / "codex" / "helper"
    helper_dir = tmp_path / "helper"
    helper_dir.mkdir()
    launcher = helper_dir / "run-codex-impl.sh"
    shutil.copy2(source_helper_dir / launcher.name, launcher)
    shutil.copy2(source_helper_dir / "codex-auth-lib.sh", helper_dir)

    marker = tmp_path / "mcp-ready"
    capture = tmp_path / "ensure-args.txt"
    ensure_mcp = helper_dir / "ensure-mcp.sh"
    ensure_mcp.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        ': >"${BIOETL_TEST_MCP_MARKER:?}"\n'
        'printf \'arg=%s\\n\' "$@" >"${BIOETL_TEST_MCP_CAPTURE:?}"\n',
        encoding="utf-8",
    )
    ensure_mcp.chmod(0o700)

    fake_codex = tmp_path / "codex-real"
    fake_codex.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        '[[ -f "${BIOETL_TEST_MCP_MARKER:?}" ]]\n'
        "printf 'codex-arg=%s\\n' \"$@\"\n",
        encoding="utf-8",
    )
    fake_codex.chmod(0o700)

    env = {
        **os.environ,
        "BIOETL_CODEX_DIRECT_BIN": str(fake_codex),
        "BIOETL_TEST_MCP_CAPTURE": str(capture),
        "BIOETL_TEST_MCP_MARKER": str(marker),
        "REPO_ROOT": str(tmp_path),
    }
    completed = subprocess.run(
        ["bash", str(launcher), "mcp", "list"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.splitlines() == [
        "codex-arg=mcp",
        "codex-arg=list",
    ]
    assert completed.stderr.splitlines() == ["[INFO] MCP configuration ready"]
    assert capture.read_text(encoding="utf-8").splitlines() == [
        "arg=--ensure",
        "arg=--codex-bin",
        f"arg={fake_codex}",
    ]


@_BASH_SUBPROCESS_UNSUPPORTED_ON_WINDOWS
def test_direct_codex_command_installer_preserves_foreign_command(
    tmp_path: Path,
) -> None:
    """Installing the shim must not overwrite an unrelated user command."""
    root = _project_root()
    ensure_helper = root / "scripts" / "ai" / "codex" / "helper" / "ensure-codex-cli.sh"
    shim_dir = tmp_path / "bin"
    shim_dir.mkdir()
    shim = shim_dir / "codex"
    shim.write_text("#!/usr/bin/env bash\necho foreign\n", encoding="utf-8")
    fake_prefix = _fake_codex_prefix(tmp_path)
    env = {
        **os.environ,
        "BIOETL_CODEX_COMMAND_SHIM_DIR": str(shim_dir),
        "CODEX_NPM_PREFIX": str(fake_prefix),
    }

    completed = subprocess.run(
        ["bash", str(ensure_helper), "--install-command-shim"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )

    assert completed.returncode != 0
    assert "Refusing to overwrite non-BioETL command" in completed.stderr
    assert shim.read_text(encoding="utf-8") == "#!/usr/bin/env bash\necho foreign\n"


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


def test_setup_delegates_shared_start_timeout_to_mcp_ensure() -> None:
    """Cold shared startup has one profile-aware timeout owner."""
    root = _project_root()
    setup_helper = (
        root / "scripts" / "ai" / "codex" / "helper" / "setup-env.sh"
    ).read_text(encoding="utf-8")
    ensure_helper = (
        root / "scripts" / "ai" / "codex" / "helper" / "ensure-mcp.sh"
    ).read_text(encoding="utf-8")
    launcher_helper = (
        root / "scripts" / "ai" / "codex" / "helper" / "run-codex-impl.sh"
    ).read_text(encoding="utf-8")

    assert 'bash "${ENSURE_MCP_SCRIPT}" --ensure' in setup_helper
    assert "timeout 30 bash -c" not in setup_helper
    assert 'timeout 60 "${ENSURE_MCP_SCRIPT}"' not in launcher_helper
    assert '"${ENSURE_MCP_SCRIPT}" --ensure --codex-bin "${codex_bin}"' in (
        launcher_helper
    )
    assert "CODEX_MCP_SHARED_START_TIMEOUT:-360" in ensure_helper
    assert 'timeout "${timeout_seconds}" bash "${launcher}"' in ensure_helper
    assert "Shared-plane start phase failed" in ensure_helper
    assert "Shared-plane health verification phase failed" in ensure_helper


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
