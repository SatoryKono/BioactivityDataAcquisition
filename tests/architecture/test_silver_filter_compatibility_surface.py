"""Guardrails for retired Silver filter compatibility modes."""

from __future__ import annotations

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
ACTIVE_SURFACES = (
    ROOT / "src" / "bioetl" / "domain" / "config" / "runtime.py",
    ROOT / "src" / "bioetl" / "infrastructure" / "config" / "silver_filter_migration.py",
    ROOT / "src" / "bioetl" / "infrastructure" / "config" / "filter_config_loader.py",
    ROOT / "docs" / "filters" / "ADR-048-silver-filters-structural-scope.md",
    ROOT / "docs" / "filters" / "migration-plan.md",
)


@pytest.mark.architecture
def test_active_silver_filter_surfaces_do_not_expose_retired_legacy_mode() -> None:
    forbidden_tokens = (
        "legacy_semantic_silver",
        "BIOETL_LEGACY_SILVER_SEMANTIC",
    )
    violations: list[str] = []
    for path in ACTIVE_SURFACES:
        text = path.read_text(encoding="utf-8")
        for token in forbidden_tokens:
            if token in text:
                violations.append(f"{path.relative_to(ROOT)}: {token}")

    assert not violations, (
        "Active Silver filter surfaces must not expose retired legacy mode "
        "tokens:\n" + "\n".join(violations)
    )
