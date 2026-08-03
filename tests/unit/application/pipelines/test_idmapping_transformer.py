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
"""Unit tests for UniProt ID Mapping transformer."""

from __future__ import annotations

from unittest.mock import MagicMock
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite

import pytest

from bioetl.application.core.pre_silver_record import PreSilverRecord
from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)
from bioetl.application.pipelines.uniprot.idmapping_transformer import (
    IDMappingTransformer,
)
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunType
from tests.helpers.transformer_dependencies import build_test_transformer_dependencies


@pytest.fixture
def mock_context():
    """Create a mock pipeline context."""
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    mock_logger.warning = MagicMock()
    return PipelineContext(
        run_id=deterministic_uuid_from_callsite("test_idmapping_transformer"),
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )


@pytest.mark.unit
class TestIDMappingTransformer:
    """Tests for IDMappingTransformer."""

    @pytest.fixture
    def transformer(self):
        """Create IDMappingTransformer instance."""
        return IDMappingTransformer(
            provider="uniprot",
            entity_type="idmapping",
            dependencies=build_test_transformer_dependencies(),
        )

    @pytest.mark.asyncio
    async def test_transform_found_mapping(self, transformer, mock_context):
        """Test transformation of successful mapping."""
        record = {
            "target_id": "CHEMBL204",
            "uniprot_accession": "P00742",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["target_id"] == "CHEMBL204"
        assert result["uniprot_accession"] == "P00742"
        assert result["mapping_status"] == "found"
        assert result["_dq_warn"] is False

    @pytest.mark.asyncio
    async def test_transform_not_found_mapping(self, transformer, mock_context):
        """Test transformation when mapping not found."""
        record = {
            "target_id": "CHEMBL9999999999",
            "uniprot_accession": None,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["target_id"] == "CHEMBL9999999999"
        assert result["uniprot_accession"] is None
        assert result["mapping_status"] == "not_found"
        assert result["_dq_warn"] is True

    @pytest.mark.asyncio
    async def test_transform_entity_id_format(self, transformer, mock_context):
        """Test entity_id follows convention."""
        record = {
            "target_id": "CHEMBL204",
            "uniprot_accession": "P00742",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["entity_id"] == "uniprot:CHEMBL204"

    @pytest.mark.asyncio
    async def test_transform_entity_id_uses_canonical_target_id(
        self, transformer, mock_context
    ):
        """Entity identity must follow canonical target_id semantics, not raw input."""
        record = {
            "target_id": " chembl204 ",
            "uniprot_accession": "P00742",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["target_id"] == "CHEMBL204"
        assert result["entity_id"] == "uniprot:CHEMBL204"

    @pytest.mark.asyncio
    async def test_transform_entity_id_for_not_found(self, transformer, mock_context):
        """Test entity_id is generated even for not_found mappings."""
        record = {
            "target_id": "CHEMBL12345_INVALID",
            "uniprot_accession": None,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["entity_id"] == "uniprot:CHEMBL12345_INVALID"

    @pytest.mark.asyncio
    async def test_transform_missing_chembl_id(self, transformer, mock_context):
        """Test transformation returns None when target_id is missing."""
        record = {
            "uniprot_accession": "P00742",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None
        mock_context.logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_transform_empty_chembl_id(self, transformer, mock_context):
        """Test transformation returns None when target_id is empty."""
        record = {
            "target_id": "",
            "uniprot_accession": "P00742",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None
        mock_context.logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_transform_content_hash_present(self, transformer, mock_context):
        """Test that content_hash is generated."""
        record = {
            "target_id": "CHEMBL204",
            "uniprot_accession": "P00742",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert "content_hash" in result
        assert len(result["content_hash"]) == 64  # SHA256 hex length

    @pytest.mark.asyncio
    async def test_d_mapping_transformer__staged_payload__1ec5934a(
        self, transformer, mock_context
    ):
        """Test staged ID mapping path returns business data before hash finalization."""
        record = {
            "target_id": "CHEMBL204",
            "uniprot_accession": "P00742",
        }

        result = await transformer.transform_pre_silver(mock_context, record, index=0)

        assert isinstance(result, PreSilverRecord)
        assert result.entity_id == "uniprot:CHEMBL204"
        assert result.business_data["target_id"] == "CHEMBL204"
        assert result.business_data["mapping_status"] == "found"
        assert "content_hash" not in result.business_data

    @pytest.mark.asyncio
    async def test_d_mapping_transformer__staged_finalization__f166f7e5(
        self, transformer, mock_context
    ):
        """Legacy ID-mapping transform should match staged finalization."""
        record = {
            "target_id": "CHEMBL204",
            "uniprot_accession": "P00742",
            "protein_name": "  Test Protein  ",
        }

        pre_silver = await transformer.transform_pre_silver(
            mock_context, record, index=0
        )
        assert isinstance(pre_silver, PreSilverRecord)
        staged_result = RecordNormalizationProcessor(
            provider=transformer.provider,
        ).finalize_pre_silver(pre_silver, mock_context, 0)
        legacy_result = await transformer.transform(mock_context, record, index=0)

        assert staged_result is not None
        assert legacy_result is not None
        assert legacy_result["target_id"] == staged_result["target_id"]
        assert legacy_result["uniprot_accession"] == staged_result["uniprot_accession"]
        assert legacy_result["protein_name"] == staged_result["protein_name"]
        assert legacy_result["mapping_status"] == staged_result["mapping_status"]
        assert legacy_result["entity_id"] == staged_result["entity_id"]
        assert legacy_result["content_hash"] == staged_result["content_hash"]

    @pytest.mark.asyncio
    async def test_transform_content_hash_consistent(self, transformer, mock_context):
        """Test that content_hash is consistent for same record."""
        record = {
            "target_id": "CHEMBL204",
            "uniprot_accession": "P00742",
        }

        result1 = await transformer.transform(mock_context, record, index=0)
        result2 = await transformer.transform(mock_context, record, index=0)

        assert result1 is not None
        assert result2 is not None
        assert result1["content_hash"] == result2["content_hash"]

    @pytest.mark.asyncio
    async def test_transform_content_hash_differs_for_different_accession(
        self, transformer, mock_context
    ):
        """Test that content_hash differs when accession differs."""
        record1 = {
            "target_id": "CHEMBL204",
            "uniprot_accession": "P00742",
        }
        record2 = {
            "target_id": "CHEMBL204",
            "uniprot_accession": "P00743",
        }

        result1 = await transformer.transform(mock_context, record1, index=0)
        result2 = await transformer.transform(mock_context, record2, index=0)

        assert result1 is not None
        assert result2 is not None
        assert result1["content_hash"] != result2["content_hash"]

    @pytest.mark.asyncio
    async def test_transform_content_hash_differs_for_found_vs_not_found(
        self, transformer, mock_context
    ):
        """Test that content_hash differs for found vs not_found."""
        record_found = {
            "target_id": "CHEMBL204",
            "uniprot_accession": "P00742",
        }
        record_not_found = {
            "target_id": "CHEMBL204",
            "uniprot_accession": None,
        }

        result1 = await transformer.transform(mock_context, record_found, index=0)
        result2 = await transformer.transform(mock_context, record_not_found, index=0)

        assert result1 is not None
        assert result2 is not None
        assert result1["content_hash"] != result2["content_hash"]

    @pytest.mark.asyncio
    async def test_transform_lineage_fields_present(self, transformer, mock_context):
        """Test that lineage fields are present in result."""
        record = {
            "target_id": "CHEMBL204",
            "uniprot_accession": "P00742",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert "_run_id" in result
        assert "_run_type" in result
        assert "_source_batch_id" in result
        assert result["_source_batch_id"] is None
        assert "_ingestion_ts" in result
        assert "_index" in result

    @pytest.mark.asyncio
    async def test_transform_index_preserved(self, transformer, mock_context):
        """Test that index is preserved in result."""
        record = {
            "target_id": "CHEMBL204",
            "uniprot_accession": "P00742",
        }

        result = await transformer.transform(mock_context, record, index=42)

        assert result is not None
        assert result["_index"] == 42

    @pytest.mark.asyncio
    async def test_transform_run_type_incremental(self, transformer, mock_context):
        """Test that run_type is correctly propagated."""
        record = {
            "target_id": "CHEMBL204",
            "uniprot_accession": "P00742",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert "_run_type" in result

    @pytest.mark.asyncio
    async def test_transform_multiple_records_unique_entity_ids(
        self, transformer, mock_context
    ):
        """Test that different records get unique entity_ids."""
        records = [
            {"target_id": "CHEMBL204", "uniprot_accession": "P00742"},
            {"target_id": "CHEMBL205", "uniprot_accession": "P00915"},
            {"target_id": "CHEMBL206", "uniprot_accession": None},
        ]

        results = []
        for idx, record in enumerate(records):
            result = await transformer.transform(mock_context, record, index=idx)
            if result:
                results.append(result)

        assert len(results) == 3
        entity_ids = [r["entity_id"] for r in results]
        assert len(set(entity_ids)) == 3  # All unique

    @pytest.mark.asyncio
    async def test_transform_dq_warn_false_for_found(self, transformer, mock_context):
        """Test _dq_warn is False for found mappings."""
        record = {
            "target_id": "CHEMBL204",
            "uniprot_accession": "P00742",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["_dq_warn"] is False

    @pytest.mark.asyncio
    async def test_transform_dq_warn_true_for_not_found(
        self, transformer, mock_context
    ):
        """Test _dq_warn is True for not_found mappings."""
        record = {
            "target_id": "CHEMBL204",
            "uniprot_accession": None,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["_dq_warn"] is True

    @pytest.mark.asyncio
    async def test_d_mapping_transformer__custom_provider__1b444b2a(self, mock_context):
        """Test transformation with custom provider."""
        transformer = IDMappingTransformer(
            provider="custom_provider",
            dependencies=build_test_transformer_dependencies(),
        )
        record = {
            "target_id": "CHEMBL204",
            "uniprot_accession": "P00742",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        # Entity ID uses provider from transformer (RULES.md §2.8)
        assert result["entity_id"] == "custom_provider:CHEMBL204"

    @pytest.mark.asyncio
    async def test_transform_none_accession_vs_missing_key(
        self, transformer, mock_context
    ):
        """Test that explicit None and missing key are handled the same."""
        record_none = {
            "target_id": "CHEMBL204",
            "uniprot_accession": None,
        }
        record_missing = {
            "target_id": "CHEMBL204",
            # uniprot_accession not present
        }

        result_none = await transformer.transform(mock_context, record_none, index=0)
        result_missing = await transformer.transform(
            mock_context, record_missing, index=1
        )

        assert result_none is not None
        assert result_missing is not None
        assert result_none["mapping_status"] == "not_found"
        assert result_missing["mapping_status"] == "not_found"
        assert result_none["_dq_warn"] is True
        assert result_missing["_dq_warn"] is True

    def test_idmapping_transformer_accepts_pii_hasher(self):
        """IDMappingTransformer MUST accept pii_hasher parameter."""
        from bioetl.domain.ports.noop import NoOpPiiHasher
        from tests.helpers.transformer_dependencies import (
            build_test_transformer_dependencies,
        )

        pii_hasher = NoOpPiiHasher()
        deps = build_test_transformer_dependencies()
        transformer = IDMappingTransformer(
            pii_hasher=pii_hasher,
            dependencies=deps,
        )
        assert transformer._pii_hasher is pii_hasher
