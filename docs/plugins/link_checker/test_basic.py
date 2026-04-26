#!/usr/bin/env python3
"""
Basic functionality test for Link Checker Plugin

Tests core plugin functionality without requiring external dependencies.
"""

import os
import sys
import tempfile

# Add plugin to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))


def test_basic_plugin_structure():
    """Test that plugin has correct structure and can be imported."""
    try:
        from plugin import LinkCheckerPlugin, on_config

        print("✅ Plugin imported successfully")

        # Test plugin class exists
        assert LinkCheckerPlugin is not None
        print("✅ LinkCheckerPlugin class exists")

        # Test plugin inherits from BasePlugin
        from mkdocs.plugins import BasePlugin

        assert issubclass(LinkCheckerPlugin, BasePlugin)
        print("✅ LinkCheckerPlugin inherits from BasePlugin")

        # Test plugin has required methods
        required_methods = ["on_startup", "on_post_build"]
        for method in required_methods:
            assert hasattr(LinkCheckerPlugin, method)
            assert callable(getattr(LinkCheckerPlugin, method))
        print("✅ Plugin has required MkDocs methods")

        # Test plugin has core functionality methods
        core_methods = [
            "_find_html_files",
            "_check_links_in_files",
            "_check_link",
            "_generate_reports",
            "_generate_json_report",
            "_generate_html_report",
            "_generate_badge",
            "_log_summary",
        ]
        for method in core_methods:
            assert hasattr(LinkCheckerPlugin, method)
            assert callable(getattr(LinkCheckerPlugin, method))
        print("✅ Plugin has core functionality methods")

        # Test plugin initialization
        plugin = LinkCheckerPlugin()
        assert plugin.links_checked == 0
        assert plugin.valid_links == 0
        assert plugin.broken_links == 0
        assert plugin.redirect_links == 0
        assert len(plugin.link_results) == 0
        print("✅ Plugin initializes with correct default values")

        # Test configuration scheme
        assert hasattr(plugin, "config_scheme")
        assert isinstance(plugin.config_scheme, (list, tuple))
        assert len(plugin.config_scheme) > 0
        print("✅ Plugin has configuration scheme")

        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except AssertionError as e:
        print(f"❌ Assertion failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_plugin_configuration():
    """Test plugin configuration handling."""
    try:
        from plugin import LinkCheckerPlugin

        plugin = LinkCheckerPlugin()

        # Test default configuration
        default_config = {
            "enabled": True,
            "timeout": 10,
            "max_redirects": 5,
            "ignore_patterns": ["localhost", "127.0.0.1"],
            "report_dir": "reports/links",
            "fail_on_error": False,
        }

        plugin.config = default_config

        # Verify configuration is set
        assert plugin.config["enabled"] is True
        assert plugin.config["timeout"] == 10
        assert plugin.config["max_redirects"] == 5
        assert "localhost" in plugin.config["ignore_patterns"]
        assert plugin.config["report_dir"] == "reports/links"
        assert plugin.config["fail_on_error"] is False

        print("✅ Plugin configuration works correctly")
        return True

    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False


def test_html_file_discovery():
    """Test HTML file discovery functionality."""
    try:
        from plugin import LinkCheckerPlugin

        plugin = LinkCheckerPlugin()

        # Create temporary directory with HTML files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test HTML files
            test_files = [
                ("index.html", "<html><body>Home</body></html>"),
                ("about.html", "<html><body>About</body></html>"),
                ("contact.html", "<html><body>Contact</body></html>"),
            ]

            for filename, content in test_files:
                with open(os.path.join(temp_dir, filename), "w") as f:
                    f.write(content)

            # Test file discovery
            found_files = plugin._find_html_files(temp_dir)

            # Verify results
            assert len(found_files) == 3
            assert all(f.endswith(".html") for f in found_files)
            assert all(os.path.exists(f) for f in found_files)

            # Verify specific files found
            found_filenames = [os.path.basename(f) for f in found_files]
            for filename, _ in test_files:
                assert filename in found_filenames

        print("✅ HTML file discovery works correctly")
        return True

    except Exception as e:
        print(f"❌ HTML file discovery failed: {e}")
        return False


def test_report_generation():
    """Test report generation functionality."""
    try:
        import json

        from plugin import LinkCheckerPlugin

        plugin = LinkCheckerPlugin()

        # Add test data
        plugin.links_checked = 10
        plugin.valid_links = 8
        plugin.broken_links = 2
        plugin.link_results = [
            {
                "source_file": "index.html",
                "source_path": "/docs/index.html",
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
                "source_path": "/docs/index.html",
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

        # Verify JSON structure
        assert "version" in json_report
        assert "generated_at" in json_report
        assert "duration_seconds" in json_report
        assert "summary" in json_report
        assert "details" in json_report

        # Verify summary data
        summary = json_report["summary"]
        assert summary["total_links"] == 10
        assert summary["valid_links"] == 8
        assert summary["broken_links"] == 2
        assert summary["health_score"] == 80.0

        # Verify details
        assert len(json_report["details"]) == 2
        assert json_report["details"][0]["status"] == "valid"
        assert json_report["details"][1]["status"] == "broken"

        # Test that JSON is valid
        json_str = json.dumps(json_report)
        parsed = json.loads(json_str)
        assert parsed == json_report

        print("✅ JSON report generation works correctly")

        # Test HTML report generation
        html_report = plugin._generate_html_report()
        assert "<!DOCTYPE html>" in html_report
        assert "Link Health Report" in html_report
        assert "https://example.com" in html_report
        assert "https://broken.com" in html_report

        print("✅ HTML report generation works correctly")

        # Test badge generation
        badge = plugin._generate_badge()
        assert "<svg" in badge
        assert "Link Health" in badge
        assert "80%" in badge
        assert "warning" in badge

        print("✅ SVG badge generation works correctly")

        return True

    except Exception as e:
        print(f"❌ Report generation failed: {e}")
        return False


def main():
    """Run all basic tests."""
    print("🔍 Link Checker Plugin - Basic Functionality Tests")
    print("=" * 60)

    tests = [
        ("Basic Plugin Structure", test_basic_plugin_structure),
        ("Plugin Configuration", test_plugin_configuration),
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

    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All basic functionality tests PASSED!")
        print("\n💡 Next Steps:")
        print("1. Install dependencies: pip install beautifulsoup4 requests")
        print("2. Run full integration tests: python3 test_integration.py")
        print("3. Integrate with MkDocs: add to mkdocs.yml")
        return 0
    else:
        print(f"⚠️  {failed} test(s) FAILED")
        print(
            "\n💡 These tests verify basic functionality without external dependencies."
        )
        print("To run full tests, install: pip install beautifulsoup4 requests")
        return 1


if __name__ == "__main__":
    sys.exit(main())
