#!/usr/bin/env python3
"""
Integration test for Link Checker Plugin

Tests that the plugin can be properly imported, initialized, and configured.
"""

import os
import sys
import tempfile

# Add the plugin directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def test_plugin_import():
    """Test that the plugin can be imported."""
    try:
        from docs.plugins.link_checker.plugin import LinkCheckerPlugin

        print("✅ Plugin imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import plugin: {e}")
        return False


def test_plugin_initialization():
    """Test that the plugin can be initialized."""
    try:
        from docs.plugins.link_checker.plugin import LinkCheckerPlugin

        plugin = LinkCheckerPlugin()
        print("✅ Plugin initialized successfully")

        # Test default configuration
        assert hasattr(plugin, "config_scheme")
        assert plugin.links_checked == 0
        assert plugin.valid_links == 0
        assert plugin.broken_links == 0
        assert plugin.redirect_links == 0
        assert len(plugin.link_results) == 0

        print("✅ Plugin default state verified")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize plugin: {e}")
        return False


def test_plugin_configuration():
    """Test plugin configuration."""
    try:
        from docs.plugins.link_checker.plugin import LinkCheckerPlugin

        plugin = LinkCheckerPlugin()

        # Test configuration scheme
        config_scheme = dict(plugin.config_scheme)
        assert "enabled" in config_scheme
        assert "timeout" in config_scheme
        assert "max_redirects" in config_scheme
        assert "ignore_patterns" in config_scheme
        assert "report_dir" in config_scheme
        assert "fail_on_error" in config_scheme

        print("✅ Plugin configuration scheme verified")

        # Test setting configuration
        plugin.config = {
            "enabled": True,
            "timeout": 15,
            "max_redirects": 5,
            "ignore_patterns": ["localhost", "127.0.0.1"],
            "report_dir": "reports/links",
            "fail_on_error": False,
        }

        assert plugin.config["enabled"] is True
        assert plugin.config["timeout"] == 15
        assert plugin.config["max_redirects"] == 5
        assert "localhost" in plugin.config["ignore_patterns"]
        assert plugin.config["report_dir"] == "reports/links"
        assert plugin.config["fail_on_error"] is False

        print("✅ Plugin configuration verified")
        return True
    except Exception as e:
        print(f"❌ Failed to configure plugin: {e}")
        return False


def test_plugin_methods():
    """Test that plugin methods exist and are callable."""
    try:
        from docs.plugins.link_checker.plugin import LinkCheckerPlugin

        plugin = LinkCheckerPlugin()

        # Test that required methods exist
        assert hasattr(plugin, "on_startup")
        assert hasattr(plugin, "on_post_build")
        assert hasattr(plugin, "_find_html_files")
        assert hasattr(plugin, "_check_links_in_files")
        assert hasattr(plugin, "_check_link")
        assert hasattr(plugin, "_generate_reports")
        assert hasattr(plugin, "_generate_json_report")
        assert hasattr(plugin, "_generate_html_report")
        assert hasattr(plugin, "_generate_badge")
        assert hasattr(plugin, "_log_summary")

        # Test that methods are callable
        assert callable(plugin.on_startup)
        assert callable(plugin.on_post_build)
        assert callable(plugin._find_html_files)
        assert callable(plugin._check_links_in_files)
        assert callable(plugin._check_link)
        assert callable(plugin._generate_reports)
        assert callable(plugin._generate_json_report)
        assert callable(plugin._generate_html_report)
        assert callable(plugin._generate_badge)
        assert callable(plugin._log_summary)

        print("✅ Plugin methods verified")
        return True
    except Exception as e:
        print(f"❌ Failed to verify plugin methods: {e}")
        return False


def test_html_file_discovery():
    """Test HTML file discovery functionality."""
    try:
        from docs.plugins.link_checker.plugin import LinkCheckerPlugin

        plugin = LinkCheckerPlugin()

        # Create temporary directory with HTML files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create some HTML files
            for i in range(3):
                with open(os.path.join(temp_dir, f"page{i}.html"), "w") as f:
                    f.write(f"<html><body>Page {i}</body></html>")

            # Test finding files
            html_files = plugin._find_html_files(temp_dir)

            assert len(html_files) == 3
            assert all(f.endswith(".html") for f in html_files)
            assert all(os.path.exists(f) for f in html_files)

        print("✅ HTML file discovery verified")
        return True
    except Exception as e:
        print(f"❌ Failed to test HTML file discovery: {e}")
        return False


def test_report_generation():
    """Test report generation functionality."""
    try:
        from docs.plugins.link_checker.plugin import LinkCheckerPlugin

        plugin = LinkCheckerPlugin()

        # Add some test data
        plugin.links_checked = 10
        plugin.valid_links = 8
        plugin.broken_links = 2
        plugin.link_results = [
            {
                "source_file": "index.html",
                "source_path": "/path/to/index.html",
                "link_url": "https://example.com",
                "link_text": "Example",
                "status": "valid",
                "http_code": 200,
                "redirect_chain": [],
                "is_internal": False,
                "error": None,
            },
            {
                "source_file": "index.html",
                "source_path": "/path/to/index.html",
                "link_url": "https://broken.com",
                "link_text": "Broken",
                "status": "broken",
                "http_code": 404,
                "redirect_chain": [],
                "is_internal": False,
                "error": "Not Found",
            },
        ]

        # Test JSON report generation
        json_report = plugin._generate_json_report()
        assert json_report["version"] == "1.0"
        assert json_report["summary"]["total_links"] == 10
        assert json_report["summary"]["valid_links"] == 8
        assert json_report["summary"]["broken_links"] == 2
        assert json_report["summary"]["health_score"] == 80.0
        assert len(json_report["details"]) == 2

        # Test HTML report generation
        html_report = plugin._generate_html_report()
        assert "<!DOCTYPE html>" in html_report
        assert "Link Health Report" in html_report
        assert "Summary" in html_report
        assert "Details" in html_report
        assert "https://example.com" in html_report
        assert "https://broken.com" in html_report

        # Test badge generation
        badge = plugin._generate_badge()
        assert "<svg" in badge
        assert "Link Health" in badge
        assert "80%" in badge
        assert "warning" in badge

        print("✅ Report generation verified")
        return True
    except Exception as e:
        print(f"❌ Failed to test report generation: {e}")
        return False


def main():
    """Run all integration tests."""
    print("🔍 Link Checker Plugin Integration Tests")
    print("=" * 50)

    tests = [
        ("Plugin Import", test_plugin_import),
        ("Plugin Initialization", test_plugin_initialization),
        ("Plugin Configuration", test_plugin_configuration),
        ("Plugin Methods", test_plugin_methods),
        ("HTML File Discovery", test_html_file_discovery),
        ("Report Generation", test_report_generation),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        print(f"\n📋 {test_name}...")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                failed += 1
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} FAILED with exception: {e}")

    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All integration tests PASSED!")
        return 0
    else:
        print(f"⚠️  {failed} test(s) FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
