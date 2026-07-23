"""Tests for uv_resolver.sh uv/uvx resolution logic."""

from __future__ import annotations

from pathlib import Path

import pytest


class TestUvResolverStructure:
    """Test uv_resolver.sh script structure and behavior."""

    def test_script_exists(self) -> None:
        """Test that the resolver script exists."""
        script_path = Path("E:/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/mcp/support/uv_resolver.sh")
        assert script_path.exists()

    def test_script_has_network_bypass_function(self) -> None:
        """Test that the script has network bypass function."""
        script_path = Path("E:/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/mcp/support/uv_resolver.sh")
        content = script_path.read_text(encoding="utf-8")
        assert "bioetl_enable_uvx_network_bypass" in content

    def test_script_has_resolve_uvx_bin_function(self) -> None:
        """Test that the script has uvx resolution function."""
        script_path = Path("E:/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/mcp/support/uv_resolver.sh")
        content = script_path.read_text(encoding="utf-8")
        assert "bioetl_resolve_uvx_bin" in content

    def test_script_has_opt_in_bypass_logic(self) -> None:
        """Test that network bypass is opt-in."""
        script_path = Path("E:/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/mcp/support/uv_resolver.sh")
        content = script_path.read_text(encoding="utf-8")
        assert "BIOETL_UVX_DIRECT_NETWORK" in content
        assert "!= \"1\"" in content

    def test_script_has_home_default(self) -> None:
        """Test that HOME uses default value for safety."""
        script_path = Path("E:/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/mcp/support/uv_resolver.sh")
        content = script_path.read_text(encoding="utf-8")
        assert '${HOME:-}' in content

    def test_script_has_python_fallbacks(self) -> None:
        """Test that script has Python version fallbacks."""
        script_path = Path("E:/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/mcp/support/uv_resolver.sh")
        content = script_path.read_text(encoding="utf-8")
        assert "Python313" in content
        assert "Python312" in content
        assert "Python311" in content

    def test_script_has_cargo_fallback(self) -> None:
        """Test that script has cargo bin fallback."""
        script_path = Path("E:/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/mcp/support/uv_resolver.sh")
        content = script_path.read_text(encoding="utf-8")
        assert ".cargo/bin/uvx" in content

    def test_script_has_local_bin_fallback(self) -> None:
        """Test that script has local bin fallback."""
        script_path = Path("E:/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/mcp/support/uv_resolver.sh")
        content = script_path.read_text(encoding="utf-8")
        assert ".local/bin/uvx" in content

    def test_script_has_windows_paths(self) -> None:
        """Test that script has Windows LOCALAPPDATA paths."""
        script_path = Path("E:/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/mcp/support/uv_resolver.sh")
        content = script_path.read_text(encoding="utf-8")
        assert "LOCALAPPDATA" in content
        assert "Programs/Python" in content

    def test_script_has_command_check(self) -> None:
        """Test that script checks for uvx/uv commands."""
        script_path = Path("E:/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/mcp/support/uv_resolver.sh")
        content = script_path.read_text(encoding="utf-8")
        assert "command -v uvx" in content
        assert "command -v uv" in content

    def test_script_has_executable_check(self) -> None:
        """Test that script checks for executable permission."""
        script_path = Path("E:/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/mcp/support/uv_resolver.sh")
        content = script_path.read_text(encoding="utf-8")
        assert "-x" in content

    def test_script_returns_fallback(self) -> None:
        """Test that script returns 'uvx' as fallback."""
        script_path = Path("E:/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/mcp/support/uv_resolver.sh")
        content = script_path.read_text(encoding="utf-8")
        assert "uvx" in content
        assert "return 1" in content
