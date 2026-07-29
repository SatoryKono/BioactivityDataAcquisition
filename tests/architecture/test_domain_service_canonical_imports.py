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
"""Architecture guardrails for canonical domain behavior names in first-party code."""

from __future__ import annotations

import pytest

from pathlib import Path

import yaml


pytestmark = pytest.mark.architecture

ROOT = Path("src/bioetl")
REPO_ROOT = Path(__file__).resolve().parents[2]
COMPATIBILITY_INVENTORY = (
    REPO_ROOT / "configs" / "quality" / "compatibility_facade_inventory.yaml"
)
SCRIPTS_ROOT = REPO_ROOT / "scripts"
TESTS_ROOT = REPO_ROOT / "tests"
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
ALLOWED_LEGACY_REFERENCE_FILES = frozenset(
    {
        Path("tests/architecture/test_domain_service_canonical_imports.py"),
        Path("tests/architecture/test_domain_service_normalization_alias_usage.py"),
        Path("tests/architecture/test_domain_normalization_guardrails.py"),
    }
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


def test_first_party_scripts_and_tests_no_longer_import_domain_services() -> None:
    """First-party scripts/tests must migrate to the canonical behavior package."""
    roots = (SCRIPTS_ROOT, TESTS_ROOT)
    violations: list[str] = []

    for root in roots:
        for path in root.rglob("*.py"):
            rel_path = path.relative_to(REPO_ROOT)
            if rel_path in ALLOWED_LEGACY_REFERENCE_FILES:
                continue
            text = path.read_text(encoding="utf-8")
            if "bioetl.domain.services" in text:
                violations.append(rel_path.as_posix())

    assert not violations, (
        "First-party scripts/tests must not import bioetl.domain.services.\n"
        + "\n".join(sorted(violations))
    )


def test_domain_services_package_is_removed() -> None:
    """Legacy domain.services package should be removed after migration."""
    assert not (ROOT / "domain" / "services" / "__init__.py").exists()


def test_domain_services_bridge_removed_from_compatibility_inventory() -> None:
    """Compatibility inventory must not retain removed domain.services bridge rows."""
    inventory = yaml.safe_load(COMPATIBILITY_INVENTORY.read_text(encoding="utf-8"))
    rows = [
        row
        for group in ("transition_debt", "retained_entrypoints")
        for row in inventory.get(group, [])
    ]
    assert (
        next(
            (
                item
                for item in rows
                if item.get("path") == "src/bioetl/domain/services/__init__.py"
            ),
            None,
        )
        is None
    )
