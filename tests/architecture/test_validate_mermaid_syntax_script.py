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
"""Architecture tests for Mermaid syntax validator script options."""

from __future__ import annotations

import pytest

from pathlib import Path


pytestmark = pytest.mark.architecture


def _script_text() -> str:
    script_path = Path("scripts/diagrams/validate_mermaid_syntax.sh")
    assert script_path.exists(), (
        "scripts/diagrams/validate_mermaid_syntax.sh must exist"
    )
    return script_path.read_text(encoding="utf-8")


def test_validator_supports_scope_option() -> None:
    script = _script_text()

    assert "--scope MODE" in script
    assert 'SCOPE="all"' in script
    assert "--scope)" in script
    assert "Unsupported scope: $SCOPE" in script


def test_validator_has_canonical_scope_root() -> None:
    script = _script_text()

    assert "CANONICAL_ROOT=" in script
    assert "canonical)" in script
    assert 'DOCS_ROOT="$CANONICAL_ROOT"' in script


def test_validator_retries_with_docker_fallback_when_chrome_is_missing() -> None:
    script = _script_text()

    assert "MMDC_FORCE_DOCKER=1" in script
    assert "Chrome runtime unavailable" in script


def test_validator_supports_embedded_mermaid_options() -> None:
    script = _script_text()

    assert "--include-embedded" in script
    assert "--embedded-only" in script
    assert "INCLUDE_EMBEDDED=1" in script
    assert "INCLUDE_SOURCES=0" in script
    assert "embedded-mermaid.tsv" in script
