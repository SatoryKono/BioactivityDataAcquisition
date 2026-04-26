#!/usr/bin/env python3
"""
Test suite for BioETL Link Checker Plugin

Tests the core functionality of the link checker plugin.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from docs.plugins.link_checker.plugin import LinkCheckerPlugin


class TestLinkCheckerPlugin:
    """Test cases for LinkCheckerPlugin class."""

    def setup_method(self):
        """Setup test environment."""
        self.plugin = LinkCheckerPlugin()
        self.plugin.config = {
            "enabled": True,
            "timeout": 10,
            "max_redirects": 5,
            "ignore_patterns": ["localhost", "127.0.0.1"],
            "report_dir": "reports/links",
            "fail_on_error": False,
        }

    def test_initialization(self):
        """Test plugin initialization."""
        assert self.plugin.links_checked == 0
        assert self.plugin.valid_links == 0
        assert self.plugin.broken_links == 0
        assert self.plugin.redirect_links == 0
        assert len(self.plugin.link_results) == 0

    def test_find_html_files(self):
        """Test finding HTML files in directory."""
        # Create temporary directory with HTML files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            # Create some HTML files
            for i in range(3):
                (temp_dir_path / f"page{i}.html").write_text(
                    f"<html><body>Page {i}</body></html>",
                    encoding="utf-8",
                )

            # Create subdirectory with HTML file
            subdir = temp_dir_path / "subdir"
            subdir.mkdir()
            (subdir / "subpage.html").write_text(
                "<html><body>Sub page</body></html>",
                encoding="utf-8",
            )

            # Test finding files
            html_files = self.plugin._find_html_files(temp_dir)
            assert len(html_files) == 4
            assert all(f.endswith(".html") for f in html_files)

    def test_check_internal_link_valid(self):
        """Test checking valid internal link."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create target file
            temp_dir_path = Path(temp_dir)
            target_file = temp_dir_path / "target.html"
            target_file.write_text("<html><body>Target</body></html>", encoding="utf-8")

            # Test valid internal link
            result = self.plugin._check_link(
                "target.html",
                "Target Page",
                "index.html",
                str(temp_dir_path / "index.html"),
            )

            assert result is not None
            assert result["status"] == "valid"
            assert result["is_internal"] is True
            assert result["error"] is None

    def test_check_internal_link_broken(self):
        """Test checking broken internal link."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            # Test broken internal link
            result = self.plugin._check_link(
                "nonexistent.html",
                "Broken Link",
                "index.html",
                str(temp_dir_path / "index.html"),
            )

            assert result is not None
            assert result["status"] == "broken"
            assert result["is_internal"] is True
            assert result["error"] == "File not found"

    @patch("requests.Session.get")
    def test_check_external_link_valid(self, mock_get):
        """Test checking valid external link."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.history = []
        mock_get.return_value = mock_response

        result = self.plugin._check_link(
            "https://example.com", "Example", "index.html", "/path/to/index.html"
        )

        assert result is not None
        assert result["status"] == "valid"
        assert result["is_internal"] is False
        assert result["http_code"] == 200
        assert len(result["redirect_chain"]) == 0

    @patch("requests.Session.get")
    def test_check_external_link_broken(self, mock_get):
        """Test checking broken external link."""
        # Mock 404 response
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.history = []
        mock_get.return_value = mock_response

        result = self.plugin._check_link(
            "https://example.com/broken", "Broken", "index.html", "/path/to/index.html"
        )

        assert result is not None
        assert result["status"] == "broken"
        assert result["is_internal"] is False
        assert result["http_code"] == 404

    @patch("requests.Session.get")
    def test_check_external_link_redirect(self, mock_get):
        """Test checking external link with redirect."""
        # Mock redirect response
        mock_redirect = MagicMock()
        mock_redirect.status_code = 301
        mock_redirect.url = "https://example.com/redirect"

        mock_final = MagicMock()
        mock_final.status_code = 200
        mock_final.history = [mock_redirect]

        mock_get.return_value = mock_final

        result = self.plugin._check_link(
            "https://example.com/original",
            "Original",
            "index.html",
            "/path/to/index.html",
        )

        assert result is not None
        assert result["status"] == "redirect"
        assert result["is_internal"] is False
        assert len(result["redirect_chain"]) == 1

    def test_ignore_patterns(self):
        """Test that ignored patterns are respected."""
        result = self.plugin._check_link(
            "http://localhost/test", "Localhost", "index.html", "/path/to/index.html"
        )

        assert result is None  # Should be ignored

    def test_generate_json_report(self):
        """Test JSON report generation."""
        # Add some test results
        self.plugin.links_checked = 5
        self.plugin.valid_links = 4
        self.plugin.broken_links = 1
        self.plugin.link_results = [
            {
                "source_file": "index.html",
                "link_url": "https://example.com",
                "status": "valid",
                "is_internal": False,
            }
        ]

        report = self.plugin._generate_json_report()

        assert report["version"] == "1.0"
        assert report["summary"]["total_links"] == 5
        assert report["summary"]["valid_links"] == 4
        assert report["summary"]["broken_links"] == 1
        assert report["summary"]["health_score"] == 80.0
        assert len(report["details"]) == 1

    def test_generate_badge(self):
        """Test badge generation."""
        # Test different health scores
        test_cases = [
            (95, "#4c1", "passing"),
            (85, "#dbab09", "warning"),
            (75, "#e05d44", "failing"),
        ]

        for health_score, expected_color, expected_status in test_cases:
            self.plugin.valid_links = health_score
            self.plugin.links_checked = 100

            badge = self.plugin._generate_badge()

            assert f"{expected_color}" in badge
            assert f"{health_score}%" in badge
            assert f"{expected_status}" in badge
            assert "<svg" in badge
            assert "Link Health" in badge


def test_plugin_config_scheme():
    """Test plugin configuration scheme."""
    plugin = LinkCheckerPlugin()

    # Test default configuration
    assert plugin.config_scheme is not None
    assert len(plugin.config_scheme) == 6

    # Test configuration types
    config_options = dict(plugin.config_scheme)
    assert config_options["enabled"] is not None
    assert config_options["timeout"] is not None
    assert config_options["max_redirects"] is not None
    assert config_options["ignore_patterns"] is not None
    assert config_options["report_dir"] is not None
    assert config_options["fail_on_error"] is not None


def test_plugin_integration():
    """Test basic plugin integration."""
    plugin = LinkCheckerPlugin()

    # Test that plugin can be initialized
    assert plugin is not None

    # Test that required methods exist
    assert hasattr(plugin, "on_startup")
    assert hasattr(plugin, "on_post_build")
    assert callable(plugin.on_startup)
    assert callable(plugin.on_post_build)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
