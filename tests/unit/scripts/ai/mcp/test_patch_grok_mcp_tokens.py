"""Tests for _patch_grok_mcp_tokens.py token patching logic."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.ai.mcp._patch_grok_mcp_tokens import bump_timeouts, main, wire_ref

pytestmark = pytest.mark.unit


def test_main_never_prints_configuration_content(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Status output must not expose MCP configuration or literal secrets."""
    config_dir = tmp_path / ".grok"
    config_dir.mkdir()
    config_path = config_dir / "config.toml"
    secret_marker = "literal-secret-marker-must-not-be-logged"
    config_path.write_text(
        "\n".join(
            (
                "[mcp_servers.ref]",
                "enabled = true",
                'url = "https://api.ref.tools/mcp"',
                "startup_timeout_sec = 60",
                f'literal_token = "{secret_marker}"',
                "",
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "missing-home")

    main()

    output = capsys.readouterr().out
    assert "updated" in output
    assert "config.toml" in output
    assert secret_marker not in output
    assert "[mcp_servers.ref]" not in output


class TestBumpTimeouts:
    """Test timeout replacement logic."""

    def test_timeout_replacement_single_server(self) -> None:
        """Test that a single server timeout is replaced correctly."""
        text = """
[mcp_servers.ast-grep]
enabled = true
startup_timeout_sec = 60
"""
        result = bump_timeouts(text)
        assert "startup_timeout_sec = 180" in result
        assert "startup_timeout_sec = 60" not in result

    def test_timeout_replacement_multiple_servers(self) -> None:
        """Test that multiple server timeouts are replaced correctly."""
        text = """
[mcp_servers.ast-grep]
enabled = true
startup_timeout_sec = 60

[mcp_servers.memory]
enabled = true
startup_timeout_sec = 90
"""
        result = bump_timeouts(text)
        assert result.count("startup_timeout_sec = 180") == 2

    def test_timeout_replacement_preserves_other_servers(self) -> None:
        """Test that servers not in TIMEOUTS dict are unchanged."""
        text = """
[mcp_servers.ast-grep]
enabled = true
startup_timeout_sec = 60

[mcp_servers.unknown_server]
enabled = true
startup_timeout_sec = 120
"""
        result = bump_timeouts(text)
        assert "startup_timeout_sec = 180" in result  # ast-grep updated
        assert "startup_timeout_sec = 120" in result  # unknown unchanged

    def test_timeout_replacement_no_match(self) -> None:
        """Test that text without matching patterns is unchanged."""
        text = "no timeout here"
        result = bump_timeouts(text)
        assert result == text


class TestWireRef:
    """Test ref header wiring logic."""

    def test_wire_ref_double_quoted_url(self) -> None:
        """Test header wiring with double-quoted URL."""
        text = """
[mcp_servers.ref]
enabled = true
url = "https://api.ref.tools/mcp"
startup_timeout_sec = 60
"""
        result = wire_ref(text)
        assert 'headers = { "x-ref-api-key" = "${REF_TOOL_API_KEY}" }' in result
        assert 'url = "https://api.ref.tools/mcp"' in result

    def test_wire_ref_single_quoted_url(self) -> None:
        """Test header wiring with single-quoted URL."""
        text = """
[mcp_servers.ref]
enabled = true
url = 'https://api.ref.tools/mcp'
startup_timeout_sec = 60
"""
        result = wire_ref(text)
        assert 'headers = { \\"x-ref-api-key\\" = \\"${REF_TOOL_API_KEY}\\" }' in result
        assert "url = 'https://api.ref.tools/mcp'" in result

    def test_wire_ref_already_has_header(self) -> None:
        """Test that config with existing header is unchanged."""
        text = """
[mcp_servers.ref]
enabled = true
url = "https://api.ref.tools/mcp"
headers = { "x-ref-api-key" = "${REF_TOOL_API_KEY}" }
startup_timeout_sec = 60
"""
        result = wire_ref(text)
        assert result == text  # Should be unchanged

    def test_wire_ref_no_ref_section(self) -> None:
        """Test that config without ref section is unchanged."""
        text = """
[mcp_servers.ast-grep]
enabled = true
startup_timeout_sec = 60
"""
        result = wire_ref(text)
        assert result == text

    def test_wire_ref_ref_disabled(self) -> None:
        """Test that disabled ref section is unchanged."""
        text = """
[mcp_servers.ref]
enabled = false
url = "https://api.ref.tools/mcp"
startup_timeout_sec = 60
"""
        result = wire_ref(text)
        assert result == text  # Should be unchanged

    def test_wire_ref_wrong_url(self) -> None:
        """Test that config with wrong URL is unchanged."""
        text = """
[mcp_servers.ref]
enabled = true
url = "https://other.service.com"
startup_timeout_sec = 60
"""
        result = wire_ref(text)
        assert result == text  # Should be unchanged


class TestIdempotency:
    """Test that patching is idempotent."""

    def test_bump_timeouts_idempotent(self) -> None:
        """Test that running bump_timeouts twice produces same result."""
        text = """
[mcp_servers.ast-grep]
enabled = true
startup_timeout_sec = 60
"""
        first = bump_timeouts(text)
        second = bump_timeouts(first)
        assert first == second

    def test_wire_ref_idempotent(self) -> None:
        """Test that running wire_ref twice produces same result."""
        text = """
[mcp_servers.ref]
enabled = true
url = "https://api.ref.tools/mcp"
startup_timeout_sec = 60
"""
        first = wire_ref(text)
        second = wire_ref(first)
        assert first == second


class TestNonMatchingLayouts:
    """Test configs with non-matching ref section layouts."""

    def test_ref_section_missing_enabled(self) -> None:
        """Test that ref section without enabled field is unchanged."""
        text = """
[mcp_servers.ref]
url = "https://api.ref.tools/mcp"
startup_timeout_sec = 60
"""
        result = wire_ref(text)
        assert result == text

    def test_ref_section_missing_url(self) -> None:
        """Test that ref section without url field is unchanged."""
        text = """
[mcp_servers.ref]
enabled = true
startup_timeout_sec = 60
"""
        result = wire_ref(text)
        assert result == text

    def test_ref_section_missing_startup_timeout(self) -> None:
        """Test that ref section without startup_timeout_sec is unchanged."""
        text = """
[mcp_servers.ref]
enabled = true
url = "https://api.ref.tools/mcp"
"""
        result = wire_ref(text)
        assert result == text

    def test_ref_section_extra_fields(self) -> None:
        """Test that ref section with extra fields is unchanged (pattern mismatch)."""
        text = """
[mcp_servers.ref]
enabled = true
url = "https://api.ref.tools/mcp"
extra_field = "value"
startup_timeout_sec = 60
"""
        result = wire_ref(text)
        assert result == text  # Pattern doesn't match with extra fields
