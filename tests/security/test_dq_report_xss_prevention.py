"""Security tests for DQ report XSS prevention.

Tests that HTML DQ reports properly escape user-provided data to prevent
XSS vulnerabilities when displaying reports in web interfaces.
"""

from __future__ import annotations

import pytest

from bioetl.domain.behavior.dq_serializer import generate_html_report

pytestmark = pytest.mark.security


@pytest.mark.security
def test_html_report_escapes_check_names() -> None:
    """Test that check names with XSS attempts are properly escaped."""
    data = {
        "layer": "bronze",
        "summary": {
            "overall_status": "pass",
            "total_checks": 1,
            "passed": 1,
            "warnings": 0,
            "failed": 0,
        },
        "checks": {
            "<script>alert('xss')</script>": {
                "status": "pass",
                "details": "test",
            }
        },
    }

    html = generate_html_report(data)

    # Check that script tag is escaped
    assert "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;" in html
    assert "<script>alert('xss')</script>" not in html


@pytest.mark.security
def test_html_report_escapes_check_values() -> None:
    """Test that check values with XSS attempts are properly escaped."""
    data = {
        "layer": "bronze",
        "summary": {
            "overall_status": "pass",
            "total_checks": 1,
            "passed": 1,
            "warnings": 0,
            "failed": 0,
        },
        "checks": {
            "test_check": {
                "status": "pass",
                "details": "<img src=x onerror=alert('xss')>",
            }
        },
    }

    html = generate_html_report(data)

    # Check that img tag is escaped
    assert "&lt;img src=x onerror=alert(&#x27;xss&#x27;)&gt;" in html
    assert "<img src=x onerror=alert('xss')>" not in html


@pytest.mark.security
def test_html_report_escapes_status_values() -> None:
    """Test that status values with XSS attempts are properly escaped."""
    data = {
        "layer": "bronze",
        "summary": {
            "overall_status": "<script>alert('xss')</script>",
            "total_checks": 1,
            "passed": 1,
            "warnings": 0,
            "failed": 0,
        },
        "checks": {},
    }

    html = generate_html_report(data)

    # Check that script tag in status is escaped
    assert "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;" in html
    assert "<script>alert('xss')</script>" not in html


@pytest.mark.security
def test_html_report_escapes_layer_name() -> None:
    """Test that layer names with XSS attempts are properly escaped."""
    data = {
        "layer": "<script>alert('xss')</script>",
        "summary": {
            "overall_status": "pass",
            "total_checks": 1,
            "passed": 1,
            "warnings": 0,
            "failed": 0,
        },
        "checks": {},
    }

    html = generate_html_report(data)

    # Check that script tag in layer is escaped
    assert "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;" in html
    assert "<script>alert('xss')</script>" not in html


@pytest.mark.security
def test_html_report_escapes_dict_values() -> None:
    """Test that dict values with XSS attempts are properly escaped."""
    data = {
        "layer": "bronze",
        "summary": {
            "overall_status": "pass",
            "total_checks": 1,
            "passed": 1,
            "warnings": 0,
            "failed": 0,
        },
        "checks": {
            "test_check": {
                "status": "pass",
                "details": {"key": "<script>alert('xss')</script>"},
            }
        },
    }

    html = generate_html_report(data)

    # Check that script tag in dict value is escaped
    assert "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;" in html
    assert "<script>alert('xss')</script>" not in html


@pytest.mark.security
def test_html_report_escapes_list_values() -> None:
    """Test that list values with XSS attempts are properly escaped."""
    data = {
        "layer": "bronze",
        "summary": {
            "overall_status": "pass",
            "total_checks": 1,
            "passed": 1,
            "warnings": 0,
            "failed": 0,
        },
        "checks": {
            "test_check": {
                "status": "pass",
                "details": ["<script>alert('xss')</script>", "normal_value"],
            }
        },
    }

    html = generate_html_report(data)

    # Check that script tag in list value is escaped
    assert "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;" in html
    assert "<script>alert('xss')</script>" not in html


@pytest.mark.security
def test_html_report_escapes_unicode_xss() -> None:
    """Test that Unicode-based XSS attempts are properly escaped."""
    data = {
        "layer": "bronze",
        "summary": {
            "overall_status": "pass",
            "total_checks": 1,
            "passed": 1,
            "warnings": 0,
            "failed": 0,
        },
        "checks": {
            "test_check": {
                "status": "pass",
                "details": "\u003cscript\u003ealert('xss')\u003c/script\u003e",
            }
        },
    }

    html = generate_html_report(data)

    # Check that Unicode script tag is escaped
    assert "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;" in html
    assert "\u003cscript\u003ealert('xss')\u003c/script\u003e" not in html


@pytest.mark.security
def test_html_report_escapes_special_characters() -> None:
    """Test that special HTML characters are properly escaped."""
    data = {
        "layer": "bronze",
        "summary": {
            "overall_status": "pass",
            "total_checks": 1,
            "passed": 1,
            "warnings": 0,
            "failed": 0,
        },
        "checks": {
            "test_check": {
                "status": "pass",
                "details": "<>&\"'",
            }
        },
    }

    html = generate_html_report(data)

    # Check that special characters are escaped
    assert "&lt;&gt;&amp;&quot;&#x27;" in html
    assert "<>&\"'" not in html


@pytest.mark.security
def test_html_report_preserves_safe_content() -> None:
    """Test that safe content is not over-escaped."""
    data = {
        "layer": "bronze",
        "summary": {
            "overall_status": "pass",
            "total_checks": 1,
            "passed": 1,
            "warnings": 0,
            "failed": 0,
        },
        "checks": {
            "test_check": {
                "status": "pass",
                "details": "safe_value_123",
            }
        },
    }

    html = generate_html_report(data)

    # Check that safe content is preserved
    assert "safe_value_123" in html


@pytest.mark.security
def test_html_report_escapes_threshold_values() -> None:
    """Test that threshold values with XSS attempts are properly escaped."""
    data = {
        "layer": "bronze",
        "summary": {
            "overall_status": "pass",
            "total_checks": 1,
            "passed": 1,
            "warnings": 0,
            "failed": 0,
        },
        "checks": {},
        "thresholds": {
            "threshold_status": "<script>alert('xss')</script>",
            "soft_fail_threshold": "0.1",
            "hard_fail_threshold": "0.2",
            "current_error_rate": "0.05",
        },
    }

    html = generate_html_report(data)

    # Check that script tag in threshold status is escaped
    assert "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;" in html
    assert "<script>alert('xss')</script>" not in html


@pytest.mark.security
def test_html_report_escapes_meta_fields() -> None:
    """Test that meta fields with XSS attempts are properly escaped."""
    data = {
        "layer": "bronze",
        "summary": {
            "overall_status": "pass",
            "total_checks": 1,
            "passed": 1,
            "warnings": 0,
            "failed": 0,
        },
        "checks": {},
        "pipeline": "<script>alert('xss')</script>",
        "run_id": "<script>alert('xss')</script>",
        "timestamp": "<script>alert('xss')</script>",
    }

    html = generate_html_report(data)

    # Check that script tags in meta fields are escaped
    assert "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;" in html
    assert "<script>alert('xss')</script>" not in html
