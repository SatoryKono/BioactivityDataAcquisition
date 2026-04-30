"""Architecture guardrails for canonical domain behavior names in first-party code."""

from __future__ import annotations

from pathlib import Path


ROOT = Path("src/bioetl")
LEGACY_SYMBOLS = (
    "AuthorNormalizationService",
    "CompositeValidationService",
    "IdentityService",
    "DefaultDataNormalizationService",
    "DataNormalizationService",
    "MergedMetadataExplainabilityService",
    "NormalizationService",
    "OrganismClassificationService",
    "PhasedMigrationSupportService",
    "PreflightGovernanceService",
)


def test_first_party_src_prefers_canonical_domain_behavior_names() -> None:
    """Application/composition code should import canonical names by default."""
    violations: list[str] = []

    for path in ROOT.rglob("*.py"):
        rel_path = path.as_posix()
        text = path.read_text(encoding="utf-8")
        if "/tests/" in rel_path:
            continue
        for symbol in LEGACY_SYMBOLS:
            if symbol in text:
                violations.append(f"{rel_path}: contains legacy symbol {symbol}")

    assert not violations, (
        "First-party src should prefer canonical domain behavior names.\n"
        + "\n".join(sorted(violations))
    )
