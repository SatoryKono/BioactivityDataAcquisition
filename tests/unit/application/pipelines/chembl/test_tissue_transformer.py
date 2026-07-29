# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for TissueTransformer."""

import pytest

from bioetl.application.pipelines.chembl.tissue_transformer import TissueTransformer
from tests.helpers.transformer_dependencies import build_test_transformer_dependencies


pytestmark = pytest.mark.unit


class TestTissueTransformer:
    """Tests for TissueTransformer."""

    @pytest.fixture
    def transformer(self):
        """Create transformer instance."""
        return TissueTransformer(
            provider="chembl", dependencies=build_test_transformer_dependencies()
        )

    @pytest.fixture
    def sample_record(self):
        """Sample ChEMBL API tissue record."""
        return {
            "tissue_id": "CHEMBL3638177",
            "pref_name": "Amniotic fluid",
            "bto_id": "BTO:0000068",
            "caloha_id": "TS-0034",
            "efo_id": None,
            "uberon_id": "UBERON:0000173",
        }

    def test_entity_class_is_tissue(self, transformer):
        """Test transformer uses Tissue entity class."""
        from bioetl.domain.entities.chembl_tissue import Tissue

        assert transformer.entity_class is Tissue

    def test_tissue_transformer__primary_id_field__ed4f3328(self, transformer):
        """Test primary ID field is tissue_id."""
        assert transformer.primary_id_field == "tissue_id"

    def test_extract_business_data(self, transformer, sample_record):
        """Test business data extraction."""
        data = transformer._extract_business_data(
            sample_record,
            sample_record["tissue_id"],
        )

        assert data["tissue_id"] == "CHEMBL3638177"
        assert data["pref_name"] == "Amniotic fluid"
        assert data["bto_id"] == "BTO:0000068"
        assert data["caloha_id"] == "TS-0034"
        assert data["efo_id"] is None
        assert data["uberon_id"] == "UBERON:0000173"

    def test_extract_business_data_with_whitespace(self, transformer):
        """Test whitespace normalization."""
        record = {
            "tissue_id": "CHEMBL123",
            "pref_name": "  Test Tissue  ",
            "bto_id": "  BTO:0000001  ",
        }
        data = transformer._extract_business_data(record, "CHEMBL123")

        assert data["pref_name"] == "Test Tissue"
        assert data["bto_id"] == "BTO:0000001"
