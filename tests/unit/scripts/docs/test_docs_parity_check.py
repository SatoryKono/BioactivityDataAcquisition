"""Tests for docs_parity_check.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from scripts.docs_parity_check import DocumentationParityChecker, ParityResult

pytestmark = pytest.mark.unit


class TestDocumentationParityChecker:
    """Test documentation parity checking."""

    def test_parity_result_critical(self) -> None:
        """Test ParityResult critical detection."""
        result = ParityResult(
            total_checked=10,
            matches=5,
            mismatches=5,
            missing_docs=["doc1.md", "doc2.md"],
            missing_code=["code1.py"],
            parity_percentage=50.0,
        )

        assert result.is_critical() is True
        assert result.is_error() is True
        assert result.is_warning() is True

    def test_parity_result_error(self) -> None:
        """Test ParityResult error detection."""
        result = ParityResult(
            total_checked=10,
            matches=8,
            mismatches=2,
            missing_docs=[],
            missing_code=[],
            parity_percentage=89.9,  # Less than 90.0 to trigger error
        )

        assert result.is_critical() is False
        assert result.is_error() is True
        assert result.is_warning() is True

    def test_parity_result_warning(self) -> None:
        """Test ParityResult warning detection."""
        result = ParityResult(
            total_checked=10,
            matches=9,
            mismatches=1,
            missing_docs=[],
            missing_code=[],
            parity_percentage=95.0,
        )

        assert result.is_critical() is False
        assert result.is_error() is False
        assert result.is_warning() is False

    def test_parity_result_success(self) -> None:
        """Test ParityResult success case."""
        result = ParityResult(
            total_checked=10,
            matches=10,
            mismatches=0,
            missing_docs=[],
            missing_code=[],
            parity_percentage=100.0,
        )

        assert result.is_critical() is False
        assert result.is_error() is False
        assert result.is_warning() is False

    @patch("scripts.docs_parity_check.Path")
    def test_documentation_parity_checker_initialization(self, mock_path):
        """Test DocumentationParityChecker initialization."""
        mock_path.return_value.exists.return_value = True

        checker = DocumentationParityChecker()

        assert checker.configs_dir is not None
        assert checker.docs_dir is not None
        assert checker.pipeline_specs_dir is not None
        assert checker.entity_configs_dir is not None
        assert checker.composite_configs_dir is not None

    def test_documentation_parity_checker_extract_config_metadata_yaml(self, tmp_path: Path) -> None:
        """Test config metadata extraction from YAML."""
        # Create sample YAML file
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("name: test\nversion: 1.0.0\n", encoding="utf-8")

        checker = DocumentationParityChecker()
        metadata = checker.extract_config_metadata(config_file)

        assert metadata["name"] == "test"
        assert metadata["version"] == "1.0.0"

    def test_documentation_parity_checker_extract_config_metadata_json(self, tmp_path: Path) -> None:
        """Test config metadata extraction from JSON."""
        # Create sample JSON file
        config_file = tmp_path / "test_config.json"
        config_file.write_text('{"name": "test", "version": "1.0.0"}', encoding="utf-8")

        checker = DocumentationParityChecker()
        metadata = checker.extract_config_metadata(config_file)

        assert metadata["name"] == "test"
        assert metadata["version"] == "1.0.0"

    def test_documentation_parity_checker_extract_doc_metadata(self, tmp_path: Path) -> None:
        """Test doc metadata extraction from markdown."""
        # Create sample markdown file with front matter
        doc_file = tmp_path / "test_doc.md"
        doc_file.write_text(
            "---\ntitle: Test Doc\nentity: test_entity\nstatus: active\n---\n\n# Content\n",
            encoding="utf-8",
        )

        checker = DocumentationParityChecker()
        metadata = checker.extract_doc_metadata(doc_file)

        assert metadata["title"] == "Test Doc"
        assert metadata["entity"] == "test_entity"
        assert metadata["status"] == "active"

    def test_documentation_parity_checker_extract_doc_metadata_no_front_matter(self, tmp_path: Path) -> None:
        """Test doc metadata extraction without front matter."""
        # Create sample markdown file without front matter
        doc_file = tmp_path / "test_doc.md"
        doc_file.write_text("# Test Doc\n\nContent here\n", encoding="utf-8")

        checker = DocumentationParityChecker()
        metadata = checker.extract_doc_metadata(doc_file)

        assert metadata["title"] == "Test Doc"
        assert metadata["entity"] == "test_doc"  # Inferred from filename

    def test_documentation_parity_checker_config_entity_creation(self) -> None:
        """Test ConfigEntity creation."""
        checker = DocumentationParityChecker()
        entity = checker._config_entity(
            Path("configs/entities/chembl/molecule.yaml"), entity_type="entity"
        )

        assert entity.name == "molecule"
        assert entity.type == "entity"
        assert "chembl" in entity.path
