"""Architecture guardrails for canonical domain behavior names in first-party code."""

from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path("src/bioetl")
REPO_ROOT = Path(__file__).resolve().parents[2]
COMPATIBILITY_INVENTORY = (
    REPO_ROOT / "configs" / "quality" / "compatibility_facade_inventory.yaml"
)
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


def test_first_party_src_imports_domain_behavior_not_services_package() -> None:
    """Production code should use the role-based domain behavior surface."""
    violations: list[str] = []

    for path in ROOT.rglob("*.py"):
        rel_path = path.as_posix()
        if "/domain/services/" in rel_path or "/domain/behavior/" in rel_path:
            continue
        text = path.read_text(encoding="utf-8")
        if "bioetl.domain.services" in text:
            violations.append(rel_path)

    assert not violations, (
        "First-party src should import pure domain behavior through "
        "bioetl.domain.behavior, not the legacy services package.\n"
        + "\n".join(sorted(violations))
    )


def test_domain_services_package_is_only_compatibility_wrapper() -> None:
    """Legacy domain.services must not regain owner modules."""
    services_root = ROOT / "domain" / "services"
    files = {
        path.relative_to(services_root).as_posix()
        for path in services_root.rglob("*.py")
        if "__pycache__" not in path.parts
    }

    assert files == {"__init__.py"}


def test_domain_services_bridge_is_registered_and_time_bounded() -> None:
    """Legacy domain.services bridge must stay visible in compatibility governance."""
    inventory = yaml.safe_load(COMPATIBILITY_INVENTORY.read_text(encoding="utf-8"))
    rows = [
        row
        for group in ("transition_debt", "retained_entrypoints")
        for row in inventory.get(group, [])
    ]
    row = next(
        (
            item
            for item in rows
            if item.get("path") == "src/bioetl/domain/services/__init__.py"
        ),
        None,
    )

    assert row is not None
    assert row["canonical_target"] == "bioetl.domain.behavior"
    assert row["status"] == "compat-shim"
    assert row["internal_callers_zero"] is True
    assert row["review_date"] == "2026-09-30"
