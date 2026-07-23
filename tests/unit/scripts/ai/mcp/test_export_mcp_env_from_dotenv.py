"""Tests for export_mcp_env_from_dotenv.ps1 MCP env export logic."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[5]
EXPORT_SCRIPT = REPO_ROOT / "scripts/ai/mcp/export_mcp_env_from_dotenv.ps1"


def run_export_script(
    repo_root: Path,
    user_scope: bool = False,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run the export script and return the result."""
    cmd = [
        "pwsh",
        "-NoProfile",
        "-File",
        str(EXPORT_SCRIPT),
        "-RepoRoot",
        str(repo_root),
    ]
    if user_scope:
        cmd.append("-UserScope")

    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


class TestExportMcpEnvFromDotenv:
    """Test MCP env export script behavior."""

    def test_script_exists(self) -> None:
        """Test that the export script exists."""
        assert EXPORT_SCRIPT.exists()

    def test_script_runs_without_errors(self, tmp_path: Path) -> None:
        """Test that the script runs without syntax errors."""
        # Create minimal .env
        env_file = tmp_path / ".env"
        env_file.write_text("OPENAI_API_KEY=test_key\n", encoding="utf-8")

        result = run_export_script(tmp_path)
        # Script should run without crashing (may have warnings but no errors)
        assert result.returncode == 0

    def test_process_scope_exports_keys(self, tmp_path: Path) -> None:
        """Test that process scope exports keys from .env."""
        env_file = tmp_path / ".env"
        env_file.write_text("OPENAI_API_KEY=test_key\n", encoding="utf-8")

        result = run_export_script(tmp_path)
        assert result.returncode == 0
        assert "OPENAI_API_KEY" in result.stdout
        assert "set (len=" in result.stdout

    def test_user_scope_flag_accepted(self, tmp_path: Path) -> None:
        """Test that -UserScope flag is accepted."""
        env_file = tmp_path / ".env"
        env_file.write_text("OPENAI_API_KEY=test_key\n", encoding="utf-8")

        result = run_export_script(tmp_path, user_scope=True)
        assert result.returncode == 0
        assert "User-scope updates applied" in result.stdout

    def test_empty_env_reports_zero_keys(self, tmp_path: Path) -> None:
        """Test that empty .env reports zero exported keys."""
        env_file = tmp_path / ".env"
        env_file.write_text("", encoding="utf-8")

        result = run_export_script(tmp_path)
        assert result.returncode == 0
        assert "0 MCP-related keys present" in result.stdout

    def test_script_uses_provided_repo_root(self, tmp_path: Path) -> None:
        """Test that script uses the provided repo root."""
        env_file = tmp_path / ".env"
        env_file.write_text("OPENAI_API_KEY=test_key\n", encoding="utf-8")

        result = run_export_script(tmp_path)
        assert result.returncode == 0

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
        assert result.returncode == 0
        # Should export at least 3 keys
        assert "OPENAI_API_KEY" in result.stdout
        assert "NEO4J_URI" in result.stdout
        assert "GITHUB_TOKEN" in result.stdout

    def test_process_only_message_without_user_scope(self, tmp_path: Path) -> None:
        """Test that process-only message is shown without -UserScope."""
        env_file = tmp_path / ".env"
        env_file.write_text("OPENAI_API_KEY=test_key\n", encoding="utf-8")

        result = run_export_script(tmp_path, user_scope=False)
        assert result.returncode == 0
        assert "Process-only" in result.stdout
        assert "User-scope" not in result.stdout

    def test_known_mcp_keys_listed(self) -> None:
        """Test that the script lists known MCP keys."""
        content = EXPORT_SCRIPT.read_text(encoding="utf-8")

        # Check for known MCP keys in the script
        known_keys = [
            "GITHUB_TOKEN",
            "OPENAI_API_KEY",
            "NEO4J_URI",
            "REF_TOOL_API_KEY",
            "BRAVE_API_KEY",
        ]
        for key in known_keys:
            assert key in content, f"Known MCP key {key} not found in script"
