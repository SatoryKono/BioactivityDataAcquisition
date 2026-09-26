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
"""Architecture tests for publication-classification test bootstrap policy."""

from __future__ import annotations

import pytest

from pathlib import Path


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
TESTS_CONFTST = ROOT / "tests" / "conftest.py"
UNIT_CONFTST = ROOT / "tests" / "unit" / "conftest.py"


def test_session_level_bootstrap_no_longer_targets_unit_publication_suites() -> None:
    content = TESTS_CONFTST.read_text(encoding="utf-8")
    prefix_block = content[
        content.index("_PUBLICATION_CLASSIFICATION_TEST_PREFIXES") : content.index(
            "_HYPOTHESIS_TEST_PREFIXES"
        )
    ]

    assert "tests/unit/" not in prefix_block
    assert "tests/integration/" in prefix_block
    assert "tests/e2e/" in prefix_block


def test_unit_publication_bootstrap_is_explicit_local_fixture() -> None:
    content = UNIT_CONFTST.read_text(encoding="utf-8")

    assert "publication_type_classification_data" in content
    assert "initialize_test_publication_type_classification" in content
