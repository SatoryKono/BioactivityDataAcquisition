"""Unit tests for ChEMBL watermark extractors."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.application.pipelines.chembl.assay_watermark import AssayWatermarkExtractor
from bioetl.application.pipelines.chembl.document_watermark import (
    DocumentWatermarkExtractor,
)
from bioetl.application.pipelines.chembl.molecule_watermark import (
    MoleculeWatermarkExtractor,
)
from bioetl.application.pipelines.chembl.target_watermark import (
    TargetWatermarkExtractor,
)
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunID, RunType


@pytest.fixture
def mock_context():
    """Create a mock pipeline context."""
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    return PipelineContext(
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )


@pytest.mark.unit
class TestAssayWatermarkExtractor:
    """Tests for AssayWatermarkExtractor."""

    def test_init_default(self):
        """Test initialization with default watermark field."""
        extractor = AssayWatermarkExtractor()
        assert extractor.watermark_field is None

    def test_init_with_field(self):
        """Test initialization with custom watermark field."""
        extractor = AssayWatermarkExtractor(watermark_field="custom_field")
        assert extractor.watermark_field == "custom_field"

    def test_extract_with_assay_id(self, mock_context):
        """Test extraction when assay_chembl_id is present."""
        extractor = AssayWatermarkExtractor()
        record = {"assay_chembl_id": "CHEMBL123456"}

        result = extractor.extract(mock_context, record)

        assert result.value == "CHEMBL123456"

    def test_extract_with_fallback_field(self, mock_context):
        """Test extraction using fallback watermark field."""
        extractor = AssayWatermarkExtractor(watermark_field="backup_id")
        record = {"backup_id": "BACKUP123"}

        result = extractor.extract(mock_context, record)

        assert result.value == "BACKUP123"

    def test_extract_missing_id_returns_empty(self, mock_context):
        """Test extraction returns empty watermark when ID is missing."""
        extractor = AssayWatermarkExtractor()
        record = {"other_field": "value"}

        result = extractor.extract(mock_context, record)

        assert result.value == ""

    def test_extract_numeric_id_converted_to_string(self, mock_context):
        """Test extraction converts numeric ID to string."""
        extractor = AssayWatermarkExtractor()
        record = {"assay_chembl_id": 123456}

        result = extractor.extract(mock_context, record)

        assert result.value == "123456"

    def test_extract_prefers_primary_over_fallback(self, mock_context):
        """Test extraction prefers assay_chembl_id over fallback field."""
        extractor = AssayWatermarkExtractor(watermark_field="backup_id")
        record = {
            "assay_chembl_id": "PRIMARY123",
            "backup_id": "BACKUP123",
        }

        result = extractor.extract(mock_context, record)

        assert result.value == "PRIMARY123"


@pytest.mark.unit
class TestDocumentWatermarkExtractor:
    """Tests for DocumentWatermarkExtractor."""

    def test_init_default(self):
        """Test initialization with default watermark field."""
        extractor = DocumentWatermarkExtractor()
        assert extractor.watermark_field is None

    def test_extract_with_document_id(self, mock_context):
        """Test extraction when document_chembl_id is present."""
        extractor = DocumentWatermarkExtractor()
        record = {"document_chembl_id": "CHEMBL789012"}

        result = extractor.extract(mock_context, record)

        assert result.value == "CHEMBL789012"

    def test_extract_missing_id_returns_empty(self, mock_context):
        """Test extraction returns empty watermark when ID is missing."""
        extractor = DocumentWatermarkExtractor()
        record = {"title": "Test Document"}

        result = extractor.extract(mock_context, record)

        assert result.value == ""


@pytest.mark.unit
class TestMoleculeWatermarkExtractor:
    """Tests for MoleculeWatermarkExtractor."""

    def test_init_default(self):
        """Test initialization with default watermark field."""
        extractor = MoleculeWatermarkExtractor()
        assert extractor.watermark_field is None

    def test_extract_with_molecule_id(self, mock_context):
        """Test extraction when molecule_chembl_id is present."""
        extractor = MoleculeWatermarkExtractor()
        record = {"molecule_chembl_id": "CHEMBL25"}

        result = extractor.extract(mock_context, record)

        assert result.value == "CHEMBL25"

    def test_extract_missing_id_returns_empty(self, mock_context):
        """Test extraction returns empty watermark when ID is missing."""
        extractor = MoleculeWatermarkExtractor()
        record = {"pref_name": "Aspirin"}

        result = extractor.extract(mock_context, record)

        assert result.value == ""


@pytest.mark.unit
class TestTargetWatermarkExtractor:
    """Tests for TargetWatermarkExtractor."""

    def test_init_default(self):
        """Test initialization with default watermark field."""
        extractor = TargetWatermarkExtractor()
        assert extractor.watermark_field is None

    def test_extract_with_target_id(self, mock_context):
        """Test extraction when target_chembl_id is present."""
        extractor = TargetWatermarkExtractor()
        record = {"target_chembl_id": "CHEMBL1862"}

        result = extractor.extract(mock_context, record)

        assert result.value == "CHEMBL1862"

    def test_extract_missing_id_returns_empty(self, mock_context):
        """Test extraction returns empty watermark when ID is missing."""
        extractor = TargetWatermarkExtractor()
        record = {"pref_name": "COX-2"}

        result = extractor.extract(mock_context, record)

        assert result.value == ""

    def test_extract_numeric_id_converted(self, mock_context):
        """Test numeric ID is converted to string."""
        extractor = TargetWatermarkExtractor()
        record = {"target_chembl_id": 1862}

        result = extractor.extract(mock_context, record)

        assert result.value == "1862"
