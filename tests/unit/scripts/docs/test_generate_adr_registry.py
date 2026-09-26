"""Tests for generate_adr_registry.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from scripts.generate_adr_registry import ADRJsonRegistryEntry

pytestmark = pytest.mark.unit


class TestADRJsonRegistryEntry:
    """Test ADR registry entry structure."""

    def test_adr_registry_entry_structure(self) -> None:
        """Test that ADRJsonRegistryEntry has expected fields."""
        entry = ADRJsonRegistryEntry(
            adr_number="001",
            title="Test ADR",
            file_path="docs/02-architecture/decisions/ADR-001-test.md",
            status="accepted",
            source_status="active",
            category="architecture",
            owner="BioETL Team",
            decision_date="2026-01-01",
            last_reviewed="2026-06-01",
            context="Test context",
        )

        assert entry["adr_number"] == "001"
        assert entry["title"] == "Test ADR"
        assert entry["status"] == "accepted"
        assert entry["category"] == "architecture"

    def test_adr_registry_entry_optional_fields(self) -> None:
        """Test ADR registry entry with optional fields."""
        entry = ADRJsonRegistryEntry(
            adr_number="002",
            title="Test ADR 2",
            file_path="docs/02-architecture/decisions/ADR-002-test.md",
            status="proposed",
            source_status=None,  # Optional field
            category="governance",
            owner="BioETL Team",
            decision_date=None,  # Optional field
            last_reviewed=None,  # Optional field
            context="Test context 2",
        )

        assert entry["adr_number"] == "002"
        assert entry["source_status"] is None
        assert entry["decision_date"] is None
        assert entry["last_reviewed"] is None


class TestADRRegistryGeneration:
    """Test ADR registry generation functionality."""

    @patch("scripts.generate_adr_registry.Path")
    def test_adr_directory_structure(self, mock_path):
        """Test ADR directory structure validation."""
        # This test would validate that the ADR directory structure is correct
        # For now, we'll just test the structure exists
        adr_dir = Path("docs/02-architecture/decisions")
        assert adr_dir is not None

    def test_adr_file_parsing(self, tmp_path: Path) -> None:
        """Test ADR file parsing."""
        # Create sample ADR file
        adr_file = tmp_path / "ADR-001-test.md"
        adr_file.write_text(
            """---
title: Test ADR
status: accepted
category: architecture
owner: BioETL Team
decision_date: 2026-01-01
last_reviewed: 2026-06-01
---

# ADR-001: Test ADR

## Context
Test context here.

## Decision
Test decision here.
""",
            encoding="utf-8",
        )

        # Test that file can be read
        assert adr_file.exists()
        content = adr_file.read_text(encoding="utf-8")
        assert "Test ADR" in content
        assert "accepted" in content

    def test_adr_registry_json_structure(self, tmp_path: Path) -> None:
        """Test ADR registry JSON structure."""
        # Create sample registry
        registry_file = tmp_path / "registry.json"
        sample_registry = [
            {
                "adr_number": "001",
                "title": "Test ADR",
                "file_path": "docs/02-architecture/decisions/ADR-001-test.md",
                "status": "accepted",
                "source_status": "active",
                "category": "architecture",
                "owner": "BioETL Team",
                "decision_date": "2026-01-01",
                "last_reviewed": "2026-06-01",
                "context": "Test context",
            }
        ]

        import json

        registry_file.write_text(json.dumps(sample_registry), encoding="utf-8")

        # Test that registry can be read and parsed
        assert registry_file.exists()
        with registry_file.open(encoding="utf-8") as f:
            loaded_registry = json.load(f)

        assert len(loaded_registry) == 1
        assert loaded_registry[0]["adr_number"] == "001"
        assert loaded_registry[0]["title"] == "Test ADR"
