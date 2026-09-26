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
"""Architecture guard: maintain minimum VCR cassette coverage per provider."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

MIN_PROVIDER_CASSETTES = 20
TARGET_PROVIDERS = ("openalex", "pubmed", "semanticscholar", "crossref")


def _count_provider_cassettes(vcr_root: Path, provider: str) -> int:
    provider_dir = vcr_root / provider
    if not provider_dir.exists():
        return 0
    return len(list(provider_dir.rglob("*.yaml"))) + len(
        list(provider_dir.rglob("*.yml"))
    )


def test_provider_vcr_coverage_minimum(src_dir: Path) -> None:
    """Critical providers must each have at least 20 cassette files."""
    project_root = src_dir.parent
    vcr_root = project_root / "tests" / "fixtures" / "vcr"
    if not vcr_root.exists():
        pytest.skip("VCR fixture directory not found")

    violations: list[str] = []
    for provider in TARGET_PROVIDERS:
        count = _count_provider_cassettes(vcr_root, provider)
        if count < MIN_PROVIDER_CASSETTES:
            violations.append(
                f"{provider}: {count} cassette(s) (required >= {MIN_PROVIDER_CASSETTES})"
            )

    assert not violations, "Insufficient provider VCR coverage:\n" + "\n".join(
        f"  - {line}" for line in violations
    )
