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
"""Architecture guard for independently meaningful security test boundaries."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture
ROOT = Path(__file__).resolve().parents[2]
SECURITY_BOUNDARIES = {
    "test_api_request_metadata_sanitization.py": "src/bioetl/infrastructure/adapters/common/api_request_collector.py",
    "test_dq_report_xss_prevention.py": "src/bioetl/domain/behavior/_dq_serializer_html/_renderers.py",
    "test_exception_redaction.py": "src/bioetl/domain/exceptions/_redaction.py",
    "test_export_redaction_enforcement.py": "src/bioetl/application/services/export_lineage/export_execution.py",
    "test_pii_hashing_enforcement.py": "src/bioetl/infrastructure/security/pii_hasher.py",
    "test_pubmed_xxe_mitigation.py": "src/bioetl/infrastructure/adapters/pubmed",
    "test_security.py": "src/bioetl/infrastructure/observability/logging_config.py",
    "test_sql_injection_prevention.py": "src/bioetl/infrastructure/storage",
    "test_structured_logging_redaction.py": "src/bioetl/infrastructure/observability/logging_config.py",
    "test_xss_prevention.py": "src/bioetl/interfaces",
}


def test_security_suite_covers_at_least_ten_distinct_boundaries() -> None:
    assert len(SECURITY_BOUNDARIES) >= 10
    for test_name, production_surface in SECURITY_BOUNDARIES.items():
        test_path = ROOT / "tests" / "security" / test_name
        surface_path = ROOT / production_surface
        assert test_path.is_file(), f"Missing security test boundary: {test_path}"
        assert surface_path.exists(), (
            f"Missing production security surface: {surface_path}"
        )
        tree = ast.parse(test_path.read_text(encoding="utf-8"))
        assert any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
            for node in ast.walk(tree)
        ), f"Security boundary has no executable test: {test_path}"
