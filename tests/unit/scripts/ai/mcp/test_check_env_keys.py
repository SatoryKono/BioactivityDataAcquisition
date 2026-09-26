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
"""Tests for _check_env_keys.py .env parsing logic."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.ai.mcp._check_env_keys import load_dotenv

pytestmark = pytest.mark.unit


class TestLoadDotenv:
    """Test .env file parsing logic."""

    def test_load_dotenv_basic_parsing(self, tmp_path: Path) -> None:
        """Test basic key=value parsing."""
        env_file = tmp_path / ".env"
        env_file.write_text("KEY1=value1\nKEY2=value2\n", encoding="utf-8")
        result = load_dotenv(env_file)
        assert result == {"KEY1": "value1", "KEY2": "value2"}

    def test_load_dotenv_empty_lines(self, tmp_path: Path) -> None:
        """Test that empty lines are ignored."""
        env_file = tmp_path / ".env"
        env_file.write_text("\n\nKEY=value\n\n", encoding="utf-8")
        result = load_dotenv(env_file)
        assert result == {"KEY": "value"}

    def test_load_dotenv_comments(self, tmp_path: Path) -> None:
        """Test that comment lines are ignored."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            "# comment\nKEY=value\n# another comment\n", encoding="utf-8"
        )
        result = load_dotenv(env_file)
        assert result == {"KEY": "value"}

    def test_load_dotenv_single_quoted_values(self, tmp_path: Path) -> None:
        """Test that single-quoted values are unquoted."""
        env_file = tmp_path / ".env"
        env_file.write_text("KEY='value'\n", encoding="utf-8")
        result = load_dotenv(env_file)
        assert result == {"KEY": "value"}

    def test_load_dotenv_double_quoted_values(self, tmp_path: Path) -> None:
        """Test that double-quoted values are unquoted."""
        env_file = tmp_path / ".env"
        env_file.write_text('KEY="value"\n', encoding="utf-8")
        result = load_dotenv(env_file)
        assert result == {"KEY": "value"}

    def test_load_dotenv_values_with_spaces(self, tmp_path: Path) -> None:
        """Test that values with spaces are preserved."""
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=value with spaces\n", encoding="utf-8")
        result = load_dotenv(env_file)
        assert result == {"KEY": "value with spaces"}

    def test_load_dotenv_quoted_values_with_spaces(self, tmp_path: Path) -> None:
        """Test that quoted values with spaces are unquoted."""
        env_file = tmp_path / ".env"
        env_file.write_text('KEY="value with spaces"\n', encoding="utf-8")
        result = load_dotenv(env_file)
        assert result == {"KEY": "value with spaces"}

    def test_load_dotenv_key_without_value(self, tmp_path: Path) -> None:
        """Test that keys without values are handled."""
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=\n", encoding="utf-8")
        result = load_dotenv(env_file)
        assert result == {"KEY": ""}

    def test_load_dotenv_whitespace_stripping(self, tmp_path: Path) -> None:
        """Test that whitespace around keys and values is stripped."""
        env_file = tmp_path / ".env"
        env_file.write_text("  KEY  =  value  \n", encoding="utf-8")
        result = load_dotenv(env_file)
        assert result == {"KEY": "value"}

    def test_load_dotenv_nonexistent_file(self, tmp_path: Path) -> None:
        """Test that non-existent files return empty dict."""
        result = load_dotenv(tmp_path / "nonexistent.env")
        assert result == {}

    def test_load_dotenv_single_char_values_not_unquoted(self, tmp_path: Path) -> None:
        """Test that single-character values are not unquoted."""
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=v\n", encoding="utf-8")
        result = load_dotenv(env_file)
        assert result == {"KEY": "v"}

    def test_load_dotenv_empty_quoted_value(self, tmp_path: Path) -> None:
        """Test that empty quoted values are unquoted to empty string."""
        env_file = tmp_path / ".env"
        env_file.write_text('KEY=""\n', encoding="utf-8")
        result = load_dotenv(env_file)
        assert result == {"KEY": ""}

    def test_load_dotenv_value_with_equals_sign(self, tmp_path: Path) -> None:
        """Test that values with equals signs are handled correctly."""
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=value=with=equals\n", encoding="utf-8")
        result = load_dotenv(env_file)
        assert result == {"KEY": "value=with=equals"}

    def test_load_dotenv_quoted_value_with_equals_sign(self, tmp_path: Path) -> None:
        """Test that quoted values with equals signs are handled correctly."""
        env_file = tmp_path / ".env"
        env_file.write_text('KEY="value=with=equals"\n', encoding="utf-8")
        result = load_dotenv(env_file)
        assert result == {"KEY": "value=with=equals"}

    def test_load_dotenv_mixed_quotes(self, tmp_path: Path) -> None:
        """Test that mixed quotes are handled (only matching quotes unquoted)."""
        env_file = tmp_path / ".env"
        env_file.write_text("KEY1=\"value\"\nKEY2='value'\n", encoding="utf-8")
        result = load_dotenv(env_file)
        assert result == {"KEY1": "value", "KEY2": "value"}

    def test_load_dotenv_special_characters(self, tmp_path: Path) -> None:
        """Test that special characters in values are preserved."""
        env_file = tmp_path / ".env"
        env_file.write_text('KEY="value!@#$%^&*()"\n', encoding="utf-8")
        result = load_dotenv(env_file)
        assert result == {"KEY": "value!@#$%^&*()"}

    def test_load_dotenv_multiline_values_not_supported(self, tmp_path: Path) -> None:
        """Test that multiline values are not supported (each line processed separately)."""
        env_file = tmp_path / ".env"
        env_file.write_text('KEY="line1\nline2"\n', encoding="utf-8")
        result = load_dotenv(env_file)
        # Each line is processed separately, so this won't work as multiline
        assert "KEY" not in result or result["KEY"] != "line1\nline2"

    def test_load_dotenv_unicode_values(self, tmp_path: Path) -> None:
        """Test that unicode values are handled correctly."""
        env_file = tmp_path / ".env"
        env_file.write_text('KEY="value with unicode: café"\n', encoding="utf-8")
        result = load_dotenv(env_file)
        assert result == {"KEY": "value with unicode: café"}

    def test_load_dotenv_empty_key(self, tmp_path: Path) -> None:
        """Test that lines with empty keys are ignored."""
        env_file = tmp_path / ".env"
        env_file.write_text("=value\nKEY=value\n", encoding="utf-8")
        result = load_dotenv(env_file)
        assert result == {"KEY": "value"}

    def test_load_dotenv_line_without_equals(self, tmp_path: Path) -> None:
        """Test that lines without equals signs are ignored."""
        env_file = tmp_path / ".env"
        env_file.write_text("just a line\nKEY=value\n", encoding="utf-8")
        result = load_dotenv(env_file)
        assert result == {"KEY": "value"}
