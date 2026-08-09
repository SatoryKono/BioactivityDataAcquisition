"""Fixtures for docs script tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def temp_docs_dir(tmp_path: Path) -> Path:
    """Create a temporary docs directory for testing."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True)
    return docs_dir


@pytest.fixture
def temp_configs_dir(tmp_path: Path) -> Path:
    """Create a temporary configs directory for testing."""
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir(parents=True)
    return configs_dir


@pytest.fixture
def sample_entity_config() -> str:
    """Sample entity configuration for testing."""
    return """
name: chembl_molecule
provider: chembl
type: entity
version: 1.0.0
"""


@pytest.fixture
def sample_pipeline_doc() -> str:
    """Sample pipeline documentation for testing."""
    return """---
title: ChEMBL Molecule Pipeline
entity: chembl_molecule
type: pipeline
status: active
---

# ChEMBL Molecule Pipeline

This pipeline processes ChEMBL molecule data.
"""
