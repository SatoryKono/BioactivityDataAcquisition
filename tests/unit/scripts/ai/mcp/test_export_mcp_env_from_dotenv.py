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
"""Tests for export_mcp_env_from_dotenv.ps1 MCP env export logic."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[5]
EXPORT_SCRIPT = REPO_ROOT / "scripts" / "ai" / "mcp" / "export_mcp_env_from_dotenv.ps1"

# Keys that the export script may surface from process env / .env aliases.
_MCP_ENV_KEYS = (
    "GITHUB_TOKEN",
    "GITHUB_PERSONAL_ACCESS_TOKEN",
    "GITHUB_CDX_PERSONAL_ACCESS_TOKEN",
    "GITHUB_ANY_PERSONAL_ADjCCESS_TOKEN",
    "BRAVE_API_KEY",
    "BRAVE_SEARCH_API_KEY",
    "BRAVE_API_KEY1",
    "REF_TOOL_API_KEY",
    "CONTEXT7_API_KEY",
    "CONTEXT7_API_TOKEN",
    "UPSTASH_CONTEXT7_API_KEY",
    "OPENROUTER_API_KEY",
    "OPENAI_API_KEY",
    "NEO4J_URI",
    "NEO4J_URL",
    "NEO4J_USERNAME",
    "NEO4J_PASSWORD",
    "NEO4J_AUTH",
    "NEO4J_DATABASE",
    "HUB_PAT_TOKEN",
    "DOCKER_API_KEY",
    "DOCKERHUB_USERNAME",
    "DOCKERHUB_PAT",
    "DOCKERHUB_TOKEN",
    "DOCKERHUB_PAT_TOKEN",
    "DOCKER_USERNAME",
    "NEEDLE_API_KEY",
    "NEEDLE_TOKEN",
    "GRAFANA_SERVICE_ACCOUNT_TOKEN",
    "GRAFANA_TOKEN",
    "GRAFANA_API_KEY",
    "GRAFANA_URL",
    "PROMETHEUS_URL",
    "PROMETHEUS_TOKEN",
    "BIOETL_ENV_FILE",
    "BIOETL_REPO_ENV_LOADED",
    "BIOETL_SKIP_ENV_LOCAL",
)


def _resolve_powershell() -> str | None:
    """Return an absolute PowerShell executable usable with CreateProcess.

    Bare ``pwsh`` often resolves to a ``.bat`` shim via PATH lookup, but
    ``subprocess`` without ``shell=True`` fails with WinError 2 unless the
    absolute path (or a real ``.exe``) is used.
    """
    candidates: list[str] = []
    for name in ("pwsh.exe", "pwsh", "powershell.exe", "powershell"):
        found = shutil.which(name)
        if found and found not in candidates:
            candidates.append(found)
    for path in candidates:
        if path.lower().endswith(".exe"):
            return path
    return candidates[0] if candidates else None


POWERSHELL = _resolve_powershell()
POWERSHELL_MARK = pytest.mark.skipif(
    POWERSHELL is None,
    reason="PowerShell (pwsh or powershell) is required to run export_mcp_env_from_dotenv.ps1",
)


def _powershell_path(path: Path) -> str:
    """Translate WSL paths before passing them to Windows PowerShell."""
    if os.name == "nt" or POWERSHELL is None or not POWERSHELL.lower().endswith(".exe"):
        return str(path)
    converted = subprocess.run(
        ["wslpath", "-w", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if converted.returncode != 0:
        pytest.skip("Unable to translate WSL path for Windows PowerShell")
    return converted.stdout.strip()


def _clean_env(**updates: str | None) -> dict[str, str]:
    """Build a subprocess env without host MCP secrets leaking into assertions."""
    env = {
        name: value
        for name, value in os.environ.items()
        if name not in _MCP_ENV_KEYS and not name.startswith("NEO4J_")
    }
    for name, value in updates.items():
        if value is None:
            env.pop(name, None)
        else:
            env[name] = value
    return env


def run_export_script(
    repo_root: Path,
    user_scope: bool = False,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run the export script and return the result."""
    if POWERSHELL is None:
        raise FileNotFoundError(
            "PowerShell executable not found (pwsh/powershell). "
            "Install PowerShell or ensure it is on PATH."
        )

    export_script_arg = _powershell_path(EXPORT_SCRIPT)
    repo_path = _powershell_path(repo_root)
    if os.name != "nt" and POWERSHELL.lower().endswith(".exe"):
        # WSL-to-Windows interop constructs the Windows process environment
        # from the Windows host, so ``env=`` below cannot remove host secrets.
        # Clear the relevant variables inside PowerShell before invoking the
        # script to keep assertions independent of the developer machine.
        names = ", ".join(f"'{name}'" for name in _MCP_ENV_KEYS)
        user_scope_arg = " -UserScope" if user_scope else ""
        command = (
            f"$names = @({names}); "
            "foreach ($name in $names) { Remove-Item \"Env:$name\" -ErrorAction SilentlyContinue }; "
            f"& '{export_script_arg}' -RepoRoot '{repo_path}'{user_scope_arg}; "
            "exit $LASTEXITCODE"
        )
        cmd = [POWERSHELL, "-NoProfile", "-Command", command]
    else:
        cmd = [
            POWERSHELL,
            "-NoProfile",
            "-File",
            export_script_arg,
            "-RepoRoot",
            repo_path,
        ]
        if user_scope:
            cmd.append("-UserScope")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        env=env if env is not None else _clean_env(),
    )
    if "UtilBindVsockAnyPort" in result.stderr:
        pytest.skip("Windows PowerShell interop is unavailable in this WSL session")
    return result


class TestExportMcpEnvFromDotenv:
    """Test MCP env export script behavior."""

    def test_script_exists(self) -> None:
        """Test that the export script exists."""
        assert EXPORT_SCRIPT.exists()

    @POWERSHELL_MARK
    def test_script_runs_without_errors(self, tmp_path: Path) -> None:
        """Test that the script runs without syntax errors."""
        env_file = tmp_path / ".env"
        env_file.write_text("OPENAI_API_KEY=test_key\n", encoding="utf-8")

        result = run_export_script(tmp_path)
        assert result.returncode == 0, result.stderr or result.stdout

    @POWERSHELL_MARK
    def test_process_scope_exports_keys(self, tmp_path: Path) -> None:
        """Test that process scope exports keys from .env."""
        env_file = tmp_path / ".env"
        env_file.write_text("OPENAI_API_KEY=test_key\n", encoding="utf-8")

        result = run_export_script(tmp_path)
        assert result.returncode == 0, result.stderr or result.stdout
        assert "OPENAI_API_KEY" in result.stdout
        assert "set (len=" in result.stdout

    @POWERSHELL_MARK
    def test_user_scope_flag_accepted(self, tmp_path: Path) -> None:
        """Test that -UserScope flag is accepted.

        Uses a disposable MCP key and restores any prior User-scope value so the
        suite does not permanently overwrite host credentials.
        """
        probe_key = "REF_TOOL_API_KEY"
        probe_value = "bioetl-export-mcp-env-test-probe"
        assert POWERSHELL is not None
        previous = subprocess.run(
            [
                POWERSHELL,
                "-NoProfile",
                "-Command",
                (
                    "$v = [Environment]::GetEnvironmentVariable("
                    f"'{probe_key}', 'User'); "
                    "if ($null -eq $v) { '' } else { $v }"
                ),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        previous_user_scope = (previous.stdout or "").rstrip("\r\n")

        env_file = tmp_path / ".env"
        env_file.write_text(f"{probe_key}={probe_value}\n", encoding="utf-8")

        try:
            result = run_export_script(tmp_path, user_scope=True)
            assert result.returncode == 0, result.stderr or result.stdout
            assert "User-scope updates applied" in result.stdout
        finally:
            if previous_user_scope:
                restore_literal = previous_user_scope.replace("'", "''")
                restore_expr = (
                    "[Environment]::SetEnvironmentVariable("
                    f"'{probe_key}', '{restore_literal}', 'User')"
                )
            else:
                restore_expr = (
                    "[Environment]::SetEnvironmentVariable("
                    f"'{probe_key}', $null, 'User')"
                )
            subprocess.run(
                [POWERSHELL, "-NoProfile", "-Command", restore_expr],
                capture_output=True,
                text=True,
                check=False,
            )

    @POWERSHELL_MARK
    def test_empty_env_reports_zero_keys(self, tmp_path: Path) -> None:
        """Test that empty .env reports zero exported keys."""
        env_file = tmp_path / ".env"
        env_file.write_text("", encoding="utf-8")

        result = run_export_script(tmp_path)
        assert result.returncode == 0, result.stderr or result.stdout
        assert "0 MCP-related keys present" in result.stdout

    @POWERSHELL_MARK
    def test_script_uses_provided_repo_root(self, tmp_path: Path) -> None:
        """Test that script uses the provided repo root."""
        env_file = tmp_path / ".env"
        env_file.write_text("OPENAI_API_KEY=test_key\n", encoding="utf-8")

        result = run_export_script(tmp_path)
        assert result.returncode == 0, result.stderr or result.stdout

    @POWERSHELL_MARK
    def test_script_handles_multiple_keys(self, tmp_path: Path) -> None:
        """Test that script handles multiple MCP keys."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            "OPENAI_API_KEY=test1\n"
            "NEO4J_URI=bolt://localhost:7687\n"
            "GITHUB_TOKEN=ghp_test\n",
            encoding="utf-8",
        )

        result = run_export_script(tmp_path)
        assert result.returncode == 0, result.stderr or result.stdout
        assert "OPENAI_API_KEY" in result.stdout
        assert "NEO4J_URI" in result.stdout
        assert "GITHUB_TOKEN" in result.stdout

    @POWERSHELL_MARK
    def test_process_only_message_without_user_scope(self, tmp_path: Path) -> None:
        """Test that process-only message is shown without -UserScope."""
        env_file = tmp_path / ".env"
        env_file.write_text("OPENAI_API_KEY=test_key\n", encoding="utf-8")

        result = run_export_script(tmp_path, user_scope=False)
        assert result.returncode == 0, result.stderr or result.stdout
        assert "Process-only" in result.stdout
        assert "User-scope updates applied" not in result.stdout

    def test_known_mcp_keys_listed(self) -> None:
        """Test that the script lists known MCP keys."""
        content = EXPORT_SCRIPT.read_text(encoding="utf-8")

        known_keys = [
            "GITHUB_TOKEN",
            "OPENAI_API_KEY",
            "NEO4J_URI",
            "REF_TOOL_API_KEY",
            "BRAVE_API_KEY",
        ]
        for key in known_keys:
            assert key in content, f"Known MCP key {key} not found in script"
