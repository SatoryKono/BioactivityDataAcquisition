"""Guard tests for publication alias sunset plan (RF-008.3).

Tracks the existence of legacy publication aliases scheduled for removal
after ``LEGACY_PUBLICATION_ALIASES_CUTOFF_DATE`` (2026-06-30).

These tests will start **failing** after the cutoff date, signalling
that the aliases must be removed from production code.
"""

from __future__ import annotations

from datetime import date

import pytest

from bioetl.application.core.publication_aliases import (
    LEGACY_PUBLICATION_ALIASES_CUTOFF_DATE,
    PUBLICATION_SCHEMA_FIELD_ALIASES,
)
from bioetl.domain.registry.publication_data import (
    LEGACY_PUBLICATION_ALIASES,
)


_CUTOFF = date.fromisoformat(LEGACY_PUBLICATION_ALIASES_CUTOFF_DATE)


@pytest.mark.architecture
class TestPublicationAliasSunset:
    """Guard tests for publication alias sunset timeline."""

    def test_cutoff_date_is_valid_iso_format(self) -> None:
        """Cutoff date string must be parseable as ISO date."""
        parsed = date.fromisoformat(LEGACY_PUBLICATION_ALIASES_CUTOFF_DATE)
        assert parsed.year >= 2026
        assert parsed.month >= 1

    def test_field_aliases_exist_before_cutoff(self) -> None:
        """8 field aliases must exist until cutoff; fail after to force cleanup."""
        today = date.today()
        if today <= _CUTOFF:
            assert len(PUBLICATION_SCHEMA_FIELD_ALIASES) == 8, (
                f"Expected 8 field aliases before cutoff, got "
                f"{len(PUBLICATION_SCHEMA_FIELD_ALIASES)}"
            )
        else:
            assert len(PUBLICATION_SCHEMA_FIELD_ALIASES) == 0, (
                f"Cutoff {_CUTOFF} has passed — remove all field aliases "
                f"from publication_aliases.py (RF-008.3)"
            )

    def test_entity_legacy_aliases_exist_before_cutoff(self) -> None:
        """3 entity legacy aliases must exist until cutoff; fail after."""
        today = date.today()
        expected_aliases = {"document", "document_similarity", "document_term"}
        if today <= _CUTOFF:
            assert LEGACY_PUBLICATION_ALIASES == expected_aliases, (
                f"Expected {expected_aliases}, got {LEGACY_PUBLICATION_ALIASES}"
            )
        else:
            assert len(LEGACY_PUBLICATION_ALIASES) == 0, (
                f"Cutoff {_CUTOFF} has passed — remove legacy entity aliases "
                f"from publication_data.py (RF-008.3)"
            )

    def test_no_document_entity_type_in_pipeline_configs(self) -> None:
        """Pipeline configs must not use 'document' as entity type."""
        from pathlib import Path

        configs_root = Path(__file__).resolve().parents[2] / "configs"
        configs_dir = configs_root / "entities"
        if not configs_dir.exists():
            configs_dir = configs_root
        if not configs_dir.exists():
            pytest.skip("configs/ not found")

        violations: list[str] = []
        for yaml_file in configs_dir.rglob("*.yaml"):
            try:
                content = yaml_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            # Simple check: entity_type value should not be bare "document"
            for i, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("entity_type:") or stripped.startswith("entity:"):
                    value = stripped.split(":", 1)[1].strip().strip("'\"")
                    if value == "document":
                        violations.append(f"{yaml_file.name}:{i}")

        assert not violations, (
            f"Pipeline configs use legacy 'document' entity type "
            f"(use 'publication' instead): {violations}"
        )
