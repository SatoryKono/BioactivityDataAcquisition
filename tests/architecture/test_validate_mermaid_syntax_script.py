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
