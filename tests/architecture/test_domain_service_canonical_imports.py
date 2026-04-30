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
    "OrganismClassificationService",
    "PreflightGovernanceService",
)
ALLOWED_FILES = {
    "src/bioetl/domain/services/__init__.py",
    "src/bioetl/domain/services/author_normalization_service.py",
    "src/bioetl/domain/services/composite_validation_layer.py",
    "src/bioetl/domain/services/identity_service.py",
    "src/bioetl/domain/services/data_normalization_service.py",
    "src/bioetl/domain/services/organism_classification_service.py",
    "src/bioetl/domain/services/preflight_governance.py",
}


def test_first_party_src_prefers_canonical_domain_behavior_names() -> None:
    """Application/composition code should import canonical names by default."""
    violations: list[str] = []

    for path in ROOT.rglob("*.py"):
        rel_path = path.as_posix()
        if rel_path in ALLOWED_FILES:
            continue
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
