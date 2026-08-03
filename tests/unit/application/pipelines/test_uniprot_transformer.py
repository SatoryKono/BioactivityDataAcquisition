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
"""Unit tests for UniProt Protein transformer."""

from __future__ import annotations

from functools import cache
from unittest.mock import MagicMock
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite

import pytest


@cache
def _uniprot_test_symbols() -> dict[str, object]:
    """Import UniProt transformer dependencies lazily for faster collection."""
    from bioetl.application.core.pre_silver_record import PreSilverRecord
    from bioetl.application.core.record_normalization_processor import (
        RecordNormalizationProcessor,
    )
    from bioetl.application.pipelines.uniprot.transformer import (
        UniProtProteinTransformer,
    )
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import RunType
    from tests.helpers.transformer_dependencies import instantiate_test_transformer

    return {
        "PreSilverRecord": PreSilverRecord,
        "RecordNormalizationProcessor": RecordNormalizationProcessor,
        "UniProtProteinTransformer": UniProtProteinTransformer,
        "PipelineContext": PipelineContext,
        "RunType": RunType,
        "instantiate_test_transformer": instantiate_test_transformer,
    }


def _build_transformer(**kwargs: object):
    """Create a UniProt transformer without importing it during collection."""
    symbols = _uniprot_test_symbols()
    return symbols["instantiate_test_transformer"](
        symbols["UniProtProteinTransformer"],
        **kwargs,
    )


def _build_pipeline_context(mock_logger: MagicMock):
    """Create a PipelineContext without importing runtime modules during collection."""
    symbols = _uniprot_test_symbols()
    return symbols["PipelineContext"](
        run_id=deterministic_uuid_from_callsite("test_uniprot_transformer"),
        run_type=symbols["RunType"].INCREMENTAL,
        logger=mock_logger,
    )


@pytest.fixture
def mock_context():
    """Create a mock pipeline context."""
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    mock_logger.warning = MagicMock()
    return _build_pipeline_context(mock_logger)


@pytest.mark.unit
class TestUniProtProteinTransformer:
    """Tests for UniProtProteinTransformer."""

    @pytest.fixture
    def transformer(self):
        """Create UniProtProteinTransformer instance."""
        return _build_transformer(provider="uniprot")

    @pytest.mark.asyncio
    async def test_protein_transformer__valid_record__171472be(
        self, transformer, mock_context
    ):
        """Test transformation of valid protein record with all fields."""
        record = {
            "primaryAccession": "P12345",
            "uniProtkbId": "COX2_HUMAN",
            "proteinDescription": {
                "recommendedName": {
                    "fullName": {"value": "Prostaglandin G/H synthase 2"}
                }
            },
            "genes": [{"geneName": {"value": "PTGS2"}}],
            "organism": {"taxonId": 9606},
            "sequence": {"length": 604},
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["accession"] == "P12345"
        assert result["entry_name"] == "COX2_HUMAN"
        assert result["protein_name"] == "Prostaglandin G/H synthase 2"
        assert result["gene_primary"] == "PTGS2"
        assert result["taxonomy_id"] == 9606
        assert "gene_names" not in result
        assert "organism_id" not in result
        assert result["sequence_length"] == 604
        assert "entity_id" in result
        assert "content_hash" in result
        # Lineage fields should be present
        assert "_run_id" in result
        assert "_run_type" in result
        assert "_ingestion_ts" in result

    @pytest.mark.asyncio
    async def test_transform_missing_accession(self, transformer, mock_context):
        """Test transformation returns None when primaryAccession is missing."""
        record = {
            "uniProtkbId": "TEST_HUMAN",
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "Test Protein"}}
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None
        mock_context.logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_transform_missing_entry_name(self, transformer, mock_context):
        """Test transformation returns None when uniProtkbId is missing."""
        record = {
            "primaryAccession": "P12345",
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "Test Protein"}}
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None
        mock_context.logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_transform_missing_protein_name_accepted(
        self, transformer, mock_context
    ):
        """Test transformation succeeds when protein name is missing.

        protein_name is optional - records without it should still be processed.
        """
        record = {
            "primaryAccession": "P12345",
            "uniProtkbId": "TEST_HUMAN",
            "proteinDescription": {},  # No recommendedName
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["accession"] == "P12345"
        assert result["entry_name"] == "TEST_HUMAN"
        assert result["protein_name"] is None

    @pytest.mark.asyncio
    async def test_protein_transformer__minimal_valid_record__bd1f6645(
        self, transformer, mock_context
    ):
        """Test transformation with minimal valid record (required fields only).

        Only accession and entry_name are required. protein_name is optional.
        """
        record = {
            "primaryAccession": "Q99999",
            "uniProtkbId": "MIN_HUMAN",
            # No proteinDescription - protein_name will be None
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["accession"] == "Q99999"
        assert result["entry_name"] == "MIN_HUMAN"
        assert result["protein_name"] is None
        assert result["gene_primary"] is None
        assert result.get("taxonomy_id") is None
        assert "gene_names" not in result
        assert "organism_id" not in result
        assert result.get("sequence_length") is None

    @pytest.mark.asyncio
    async def test_transform_with_multiple_genes(self, transformer, mock_context):
        """Test transformation extracts multiple gene names."""
        record = {
            "primaryAccession": "P00001",
            "uniProtkbId": "MULTI_HUMAN",
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "Multi-gene Protein"}}
            },
            "genes": [
                {"geneName": {"value": "GENE1"}},
                {"geneName": {"value": "GENE2"}},
                {"geneName": {"value": "GENE3"}},
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["gene_primary"] == "GENE1"
        assert "gene_names" not in result

    @pytest.mark.asyncio
    async def test_transform_with_empty_genes(self, transformer, mock_context):
        """Test transformation handles empty genes list."""
        record = {
            "primaryAccession": "P00002",
            "uniProtkbId": "EMPTY_HUMAN",
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "Empty Genes Protein"}}
            },
            "genes": [],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["gene_primary"] is None
        assert "gene_names" not in result

    @pytest.mark.asyncio
    async def test_protein_transformer__with_malformed_genes__2acfbb6e(
        self, transformer, mock_context
    ):
        """Test transformation handles malformed genes structure gracefully."""
        record = {
            "primaryAccession": "P00003",
            "uniProtkbId": "MAL_HUMAN",
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "Malformed Protein"}}
            },
            "genes": [
                {"geneName": {"value": "VALID"}},
                {"wrongKey": "invalid"},  # Missing geneName
                "not a dict",  # Not a dict
                {"geneName": "not a dict"},  # geneName not a dict
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["gene_primary"] == "VALID"
        assert "gene_names" not in result

    @pytest.mark.asyncio
    async def test_protein_transformer__entity_id_format__9cc7dd12(
        self, transformer, mock_context
    ):
        """Test that entity_id follows expected format."""
        record = {
            "primaryAccession": "P12345",
            "uniProtkbId": "TEST_HUMAN",
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "Test Protein"}}
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert "entity_id" in result
        # Entity ID should contain provider and accession
        assert "uniprot" in result["entity_id"]
        assert "P12345" in result["entity_id"]

    @pytest.mark.asyncio
    async def test_protein_transformer__hash_consistent__0ecaeaa4(
        self, transformer, mock_context
    ):
        """Test that content_hash is generated and is consistent."""
        record = {
            "primaryAccession": "P12345",
            "uniProtkbId": "TEST_HUMAN",
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "Test Protein"}}
            },
        }

        result1 = await transformer.transform(mock_context, record, index=0)
        result2 = await transformer.transform(mock_context, record, index=0)

        assert result1 is not None
        assert result2 is not None
        assert "content_hash" in result1
        assert "content_hash" in result2
        assert result1["content_hash"] == result2["content_hash"]

    @pytest.mark.asyncio
    async def test_protein_transformer__staged_payload__3a0f4ee3(
        self, transformer, mock_context
    ):
        """Test staged UniProt path returns business data before hash finalization."""
        record = {
            "primaryAccession": "P12345",
            "uniProtkbId": "COX2_HUMAN",
            "proteinDescription": {
                "recommendedName": {
                    "fullName": {"value": "Prostaglandin G/H synthase 2"}
                }
            },
        }

        result = await transformer.transform_pre_silver(mock_context, record, index=0)

        symbols = _uniprot_test_symbols()
        assert isinstance(result, symbols["PreSilverRecord"])
        assert result.entity_id == "uniprot:P12345"
        assert result.business_data["accession"] == "P12345"
        assert result.business_data["entry_name"] == "COX2_HUMAN"
        assert "content_hash" not in result.business_data

    @pytest.mark.asyncio
    async def test_protein_transformer__staged_finalization__e3b87098(
        self, transformer, mock_context
    ):
        """Legacy UniProt transform should match staged finalization."""
        record = {
            "primaryAccession": "P12345",
            "uniProtkbId": "COX2_HUMAN",
            "proteinDescription": {
                "recommendedName": {
                    "fullName": {"value": "Prostaglandin G/H synthase 2"}
                }
            },
            "genes": [{"geneName": {"value": "PTGS2"}}],
        }

        pre_silver = await transformer.transform_pre_silver(
            mock_context, record, index=0
        )
        symbols = _uniprot_test_symbols()
        assert isinstance(pre_silver, symbols["PreSilverRecord"])
        staged_result = symbols["RecordNormalizationProcessor"](
            provider=transformer.provider,
        ).finalize_pre_silver(pre_silver, mock_context, 0)
        legacy_result = await transformer.transform(mock_context, record, index=0)

        assert staged_result is not None
        assert legacy_result is not None
        assert legacy_result["accession"] == staged_result["accession"]
        assert legacy_result["entry_name"] == staged_result["entry_name"]
        assert legacy_result["protein_name"] == staged_result["protein_name"]
        assert legacy_result["gene_primary"] == staged_result["gene_primary"]
        assert "gene_names" not in legacy_result
        assert "gene_names" not in staged_result
        assert legacy_result["entity_id"] == staged_result["entity_id"]
        assert legacy_result["content_hash"] == staged_result["content_hash"]

    @pytest.mark.asyncio
    async def test_protein_transformer__custom_provider__1d9fde26(self, mock_context):
        """Test transformation with custom provider."""
        transformer = _build_transformer(provider="custom_uniprot")
        record = {
            "primaryAccession": "Q11111",
            "uniProtkbId": "CUST_HUMAN",
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "Custom Protein"}}
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert "custom_uniprot" in result["entity_id"]

    @pytest.mark.asyncio
    async def test_transform_empty_accession_rejected(self, transformer, mock_context):
        """Test that empty string accession is rejected."""
        record = {
            "primaryAccession": "",
            "uniProtkbId": "EMPTY_HUMAN",
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "Empty Protein"}}
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None

    @pytest.mark.asyncio
    async def test_protein_transformer__fields_present__7bcb3469(
        self, transformer, mock_context
    ):
        """Test that lineage fields are properly added to the result."""
        record = {
            "primaryAccession": "P12345",
            "uniProtkbId": "TEST_HUMAN",
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "Test Protein"}}
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        # Lineage fields should be present with underscore prefix
        assert "_run_id" in result
        assert "_run_type" in result
        assert "_source_batch_id" in result
        assert result["_source_batch_id"] is None
        assert "_ingestion_ts" in result
        # Verify types
        assert "_run_id" in result
        assert "_run_type" in result
        assert "_ingestion_ts" in result

    @pytest.mark.asyncio
    async def test_transform_sequence_length_validation(
        self, transformer, mock_context
    ):
        """Test that negative sequence_length causes validation error."""
        record = {
            "primaryAccession": "P99999",
            "uniProtkbId": "NEG_HUMAN",
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "Negative Seq Protein"}}
            },
            "sequence": {"length": -100},  # Invalid: negative
        }

        result = await transformer.transform(mock_context, record, index=0)

        # Entity validation should fail due to invariant
        assert result is None
        mock_context.logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_transform_zero_sequence_length(self, transformer, mock_context):
        """Test that zero sequence_length causes validation error."""
        record = {
            "primaryAccession": "P88888",
            "uniProtkbId": "ZERO_HUMAN",
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "Zero Seq Protein"}}
            },
            "sequence": {"length": 0},  # Invalid: zero
        }

        result = await transformer.transform(mock_context, record, index=0)

        # Entity validation should fail due to invariant
        assert result is None
        mock_context.logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_transform_deeply_nested_protein_name(
        self, transformer, mock_context
    ):
        """Test extraction of deeply nested protein name."""
        record = {
            "primaryAccession": "P77777",
            "uniProtkbId": "DEEP_HUMAN",
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "Deeply Nested Protein Name"}}
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["protein_name"] == "Deeply Nested Protein Name"

    @pytest.mark.asyncio
    async def test_transform_with_organism_taxon(self, transformer, mock_context):
        """Test extraction of organism taxon ID from nested structure."""
        record = {
            "primaryAccession": "P66666",
            "uniProtkbId": "ORG_MOUSE",
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "Mouse Protein"}}
            },
            "organism": {"taxonId": 10090},  # Mus musculus
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["taxonomy_id"] == 10090
        assert "organism_id" not in result

    def test_transformer_accepts_entity_type(self):
        """Transformer MUST accept entity_type parameter."""
        transformer = _build_transformer(entity_type="protein")
        assert transformer.entity_type == "protein"

    def test_transformer_default_entity_type(self):
        """Transformer SHOULD default entity_type to 'protein'."""
        transformer = _build_transformer()
        assert transformer.entity_type == "protein"

    def test_transformer_custom_entity_type(self):
        """Transformer MUST accept custom entity_type."""
        transformer = _build_transformer(entity_type="custom_entity")
        assert transformer.entity_type == "custom_entity"

    def test_transformer_accepts_pii_hasher(self):
        """Transformer MUST accept pii_hasher parameter."""
        from bioetl.domain.ports.noop import NoOpPiiHasher

        hasher = NoOpPiiHasher()
        transformer = _build_transformer(pii_hasher=hasher)
        assert transformer._pii_hasher is hasher

    def test_transformer_default_pii_hasher(self):
        """Transformer SHOULD default pii_hasher to NoOpPiiHasher."""
        from bioetl.domain.ports.noop import NoOpPiiHasher

        transformer = _build_transformer()
        assert isinstance(transformer._pii_hasher, NoOpPiiHasher)


@pytest.mark.unit
class TestUniProtProteinTransformerExtendedFields:
    """Tests for extended UniProt fields extraction."""

    @pytest.fixture
    def transformer(self):
        """Create UniProtProteinTransformer instance."""
        return _build_transformer(provider="uniprot")

    @pytest.mark.asyncio
    async def test_extract_entry_type_reviewed(self, transformer, mock_context):
        """Test extraction of entry type for Swiss-Prot entry."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "entryType": "UniProtKB reviewed (Swiss-Prot)",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["entry_type"] == "UniProtKB reviewed (Swiss-Prot)"
        assert result["reviewed"] is True

    @pytest.mark.asyncio
    async def test_extract_entry_type_unreviewed(self, transformer, mock_context):
        """Test extraction of entry type for TrEMBL entry."""
        record = {
            "primaryAccession": "A0A000",
            "uniProtkbId": "TEST_HUMAN",
            "entryType": "UniProtKB unreviewed (TrEMBL)",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["entry_type"] == "UniProtKB unreviewed (TrEMBL)"
        assert result["reviewed"] is False

    @pytest.mark.asyncio
    async def test_extract_secondary_accessions(self, transformer, mock_context):
        """Test extraction of secondary accessions."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "secondaryAccessions": ["Q5TEV0", "Q96QA2"],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["secondary_accessions"] == '["Q5TEV0","Q96QA2"]'

    @pytest.mark.asyncio
    async def test_extract_annotation_score(self, transformer, mock_context):
        """Test extraction of annotation score."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "annotationScore": 5,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["annotation_score"] == 5

    @pytest.mark.asyncio
    async def test_annotation_score_validation(self, transformer, mock_context):
        """Test that invalid annotation score causes validation error."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "annotationScore": 10,  # Invalid: > 5
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None
        mock_context.logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_extract_protein_existence(self, transformer, mock_context):
        """Test extraction of protein existence level."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "proteinExistence": "1: Evidence at protein level",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["protein_existence"] == "Evidence at protein level"

    @pytest.mark.asyncio
    async def test_extract_short_names(self, transformer, mock_context):
        """Test extraction of short protein names."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "proteinDescription": {
                "recommendedName": {
                    "fullName": {"value": "RAC-alpha serine/threonine-protein kinase"},
                    "shortNames": [{"value": "AKT1"}, {"value": "PKB alpha"}],
                }
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["protein_short_names"] == '["AKT1","PKB alpha"]'

    @pytest.mark.asyncio
    async def test_extract_alternative_names(self, transformer, mock_context):
        """Test extraction of alternative protein names."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "proteinDescription": {
                "alternativeNames": [
                    {"fullName": {"value": "Protein kinase B alpha"}},
                    {"fullName": {"value": "Proto-oncogene c-Akt"}},
                ]
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert (
            result["protein_alternative_names"]
            == '["Protein kinase B alpha","Proto-oncogene c-Akt"]'
        )

    @pytest.mark.asyncio
    async def test_extract_ec_numbers(self, transformer, mock_context):
        """Test extraction of EC numbers."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "proteinDescription": {
                "recommendedName": {
                    "fullName": {"value": "Test Kinase"},
                    "ecNumbers": [{"value": "2.7.11.1"}],
                }
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["protein_ec_numbers"] == '["2.7.11.1"]'

    @pytest.mark.asyncio
    async def test_extract_flag(self, transformer, mock_context):
        """Test extraction of protein flag."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "proteinDescription": {"flag": "Precursor"},
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["flag"] == "Precursor"

    @pytest.mark.asyncio
    async def test_extract_organism_info(self, transformer, mock_context):
        """Test extraction of organism information."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "organism": {
                "scientificName": "Homo sapiens",
                "commonName": "Human",
                "taxonId": 9606,
                "lineage": ["Eukaryota", "Metazoa", "Chordata"],
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["organism_scientific"] == "Homo sapiens"
        assert result["organism_common"] == "Human"
        assert result["taxonomy_id"] == 9606
        assert result["lineage"] == '["Eukaryota","Metazoa","Chordata"]'

    @pytest.mark.asyncio
    async def test_extract_gene_synonyms(self, transformer, mock_context):
        """Test extraction of gene synonyms."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "genes": [
                {
                    "geneName": {"value": "AKT1"},
                    "synonyms": [{"value": "PKB"}, {"value": "RAC"}],
                }
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["gene_primary"] == "AKT1"
        # Compact JSON format (no spaces) per centralized serialization
        assert result["gene_synonyms"] == '["PKB","RAC"]'

    @pytest.mark.asyncio
    async def test_extract_function_comment(self, transformer, mock_context):
        """Test extraction of function comment."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "comments": [
                {
                    "commentType": "FUNCTION",
                    "texts": [
                        {"value": "Serine/threonine kinase involved in cell survival."}
                    ],
                }
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert (
            result["function_comment"]
            == '["Serine/threonine kinase involved in cell survival."]'
        )

    @pytest.mark.asyncio
    async def test_extract_catalytic_activity(self, transformer, mock_context):
        """Test extraction of catalytic activity."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "comments": [
                {
                    "commentType": "CATALYTIC ACTIVITY",
                    "reaction": {
                        "name": "ATP + protein = ADP + phosphoprotein",
                        "ecNumber": "2.7.11.1",
                    },
                }
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        # Compact JSON format (no spaces after colons) per centralized serialization
        assert (
            '"reaction":"ATP + protein = ADP + phosphoprotein"'
            in result["catalytic_activity"]
        )
        assert '"ec_number":"2.7.11.1"' in result["catalytic_activity"]

    @pytest.mark.asyncio
    async def test_extract_subcellular_location(self, transformer, mock_context):
        """Test extraction of subcellular location."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "comments": [
                {
                    "commentType": "SUBCELLULAR LOCATION",
                    "subcellularLocations": [
                        {"location": {"value": "Cytoplasm"}},
                        {"location": {"value": "Nucleus"}},
                    ],
                }
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        # Compact JSON format (no spaces) per centralized serialization
        assert result["subcellular_location"] == '["Cytoplasm","Nucleus"]'

    @pytest.mark.asyncio
    async def test_extract_alternative_products(self, transformer, mock_context):
        """Test extraction of alternative products (isoforms)."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "comments": [
                {
                    "commentType": "ALTERNATIVE PRODUCTS",
                    "isoforms": [
                        {"isoformIds": ["P31749-1"], "name": {"value": "1"}},
                        {"isoformIds": ["P31749-2"], "name": {"value": "2"}},
                    ],
                }
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["isoform_count"] == 2
        # Compact JSON format per centralized serialization
        assert '"ids":["P31749-1"]' in result["alternative_products"]

    @pytest.mark.asyncio
    async def test_extract_go_terms(self, transformer, mock_context):
        """Test extraction of GO terms."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "uniProtKBCrossReferences": [
                {
                    "database": "GO",
                    "id": "GO:0005524",
                    "properties": [
                        {"key": "GoTerm", "value": "F:ATP binding"},
                        {"key": "GoEvidenceType", "value": "IEA"},
                    ],
                }
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        # Compact JSON format per centralized serialization
        assert '"id":"GO:0005524"' in result["go_terms"]
        assert '"term":"ATP binding"' in result["go_terms"]
        assert '"aspect":"F"' in result["go_terms"]
        assert '"evidence":"IEA"' in result["go_terms"]

    @pytest.mark.asyncio
    async def test_extract_drugbank_ids(self, transformer, mock_context):
        """Test extraction of DrugBank IDs."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "uniProtKBCrossReferences": [
                {"database": "DrugBank", "id": "DB00171"},
                {"database": "DrugBank", "id": "DB00734"},
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        # Compact JSON format (no spaces) per centralized serialization
        assert result["drugbank_ids"] == '["DB00171","DB00734"]'

    @pytest.mark.asyncio
    async def test_extract_chembl_ids(self, transformer, mock_context):
        """Test extraction of ChEMBL IDs."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "uniProtKBCrossReferences": [
                {"database": "ChEMBL", "id": "CHEMBL4282"},
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["chembl_ids"] == '["CHEMBL4282"]'

    @pytest.mark.asyncio
    async def test_extract_guidetopharmacology_ids(self, transformer, mock_context):
        """Test extraction of Guide to Pharmacology IDs."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "uniProtKBCrossReferences": [
                {"database": "GuidetoPHARMACOLOGY", "id": "1479"},
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["guidetopharmacology_ids"] == '["1479"]'

    @pytest.mark.asyncio
    async def test_extract_features(self, transformer, mock_context):
        """Test extraction of sequence features."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "features": [
                {
                    "type": "Chain",
                    "description": "RAC-alpha serine/threonine-protein kinase",
                    "location": {
                        "start": {"value": 1},
                        "end": {"value": 480},
                    },
                }
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["feature_count"] == 1
        # Compact JSON format per centralized serialization
        assert '"type":"Chain"' in result["features_json"]
        assert '"start":1' in result["features_json"]
        assert '"end":480' in result["features_json"]

    @pytest.mark.asyncio
    async def test_extended_fields__extract_keywords__07702d53(
        self, transformer, mock_context
    ):
        """Test extraction of UniProt keywords."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "keywords": [
                {
                    "id": "KW-0067",
                    "category": "Molecular function",
                    "name": "ATP-binding",
                },
                {"id": "KW-0418", "category": "Biological process", "name": "Kinase"},
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["keyword_count"] == 2
        # Compact JSON format per centralized serialization
        assert '"id":"KW-0067"' in result["keywords"]
        assert '"name":"ATP-binding"' in result["keywords"]
        assert '"category":"Molecular function"' in result["keywords"]

    @pytest.mark.asyncio
    async def test_extract_sequence_info(self, transformer, mock_context):
        """Test extraction of sequence information."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "sequence": {
                "value": "MSDV" * 120,  # 480 amino amolecule_ids
                "length": 480,
                "molWeight": 55686,
                "crc64": "C7E35E7E9B7C6B5A",
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["sequence_length"] == 480
        assert result["sequence_mass"] == 55686
        assert result["sequence_checksum"] == "C7E35E7E9B7C6B5A"
        assert result["sequence"] == "MSDV" * 120

    @pytest.mark.asyncio
    async def test_extract_counts(self, transformer, mock_context):
        """Test extraction of various counts."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "uniProtKBCrossReferences": [
                {"database": "GO", "id": "GO:0001"},
                {"database": "DrugBank", "id": "DB001"},
            ],
            "features": [{"type": "Chain"}, {"type": "Domain"}],
            "keywords": [{"id": "KW-0067"}],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["cross_reference_count"] == 2
        assert result["feature_count"] == 2
        assert result["keyword_count"] == 1

    @pytest.mark.asyncio
    async def test_full_record_transformation(self, transformer, mock_context):
        """Test transformation of a comprehensive UniProt record."""
        record = {
            "entryType": "UniProtKB reviewed (Swiss-Prot)",
            "primaryAccession": "P31749",
            "secondaryAccessions": ["Q5TEV0"],
            "uniProtkbId": "AKT1_HUMAN",
            "annotationScore": 5,
            "proteinExistence": "1: Evidence at protein level",
            "organism": {
                "scientificName": "Homo sapiens",
                "commonName": "Human",
                "taxonId": 9606,
                "lineage": ["Eukaryota", "Metazoa"],
            },
            "proteinDescription": {
                "recommendedName": {
                    "fullName": {"value": "RAC-alpha serine/threonine-protein kinase"},
                    "shortNames": [{"value": "AKT1"}],
                    "ecNumbers": [{"value": "2.7.11.1"}],
                },
                "alternativeNames": [{"fullName": {"value": "PKB alpha"}}],
                "flag": "Precursor",
            },
            "genes": [{"geneName": {"value": "AKT1"}, "synonyms": [{"value": "PKB"}]}],
            "comments": [
                {
                    "commentType": "FUNCTION",
                    "texts": [{"value": "Serine/threonine kinase."}],
                },
                {
                    "commentType": "SUBCELLULAR LOCATION",
                    "subcellularLocations": [{"location": {"value": "Cytoplasm"}}],
                },
            ],
            "uniProtKBCrossReferences": [
                {
                    "database": "GO",
                    "id": "GO:0005524",
                    "properties": [{"key": "GoTerm", "value": "F:ATP binding"}],
                },
                {"database": "ChEMBL", "id": "CHEMBL4282"},
            ],
            "features": [
                {
                    "type": "Chain",
                    "location": {"start": {"value": 1}, "end": {"value": 480}},
                }
            ],
            "keywords": [{"id": "KW-0067", "name": "ATP-binding"}],
            "sequence": {"value": "MSDV", "length": 480, "molWeight": 55686},
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        # Core identifiers
        assert result["accession"] == "P31749"
        assert result["entry_name"] == "AKT1_HUMAN"
        assert result["entry_type"] == "UniProtKB reviewed (Swiss-Prot)"
        assert result["reviewed"] is True
        assert result["annotation_score"] == 5
        # Organism
        assert result["organism_scientific"] == "Homo sapiens"
        assert result["taxonomy_id"] == 9606
        # Protein names
        assert result["protein_name"] == "RAC-alpha serine/threonine-protein kinase"
        assert result["protein_short_names"] == '["AKT1"]'
        assert result["flag"] == "Precursor"
        # Functional annotations
        assert result["function_comment"] == '["Serine/threonine kinase."]'
        assert result["subcellular_location"] == '["Cytoplasm"]'
        # Cross-references
        assert '"GO:0005524"' in result["go_terms"]
        assert result["chembl_ids"] == '["CHEMBL4282"]'
        # Counts
        assert result["cross_reference_count"] == 2
        assert result["feature_count"] == 1
        assert result["keyword_count"] == 1


@pytest.mark.unit
class TestUniProtTransformerAuditDates:
    """Tests for UniProt audit date extraction."""

    @pytest.fixture
    def transformer(self):
        """Create UniProtProteinTransformer instance."""
        return _build_transformer(provider="uniprot")

    @pytest.mark.asyncio
    async def test_extract_entry_audit_dates(self, transformer, mock_context):
        """Test extraction of entry audit dates from entryAudit object."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "entryAudit": {
                "firstPublicDate": "2000-12-01",
                "lastAnnotationUpdateDate": "2024-07-24",
                "entryVersion": 275,
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["entry_created"] == "2000-12-01"
        assert result["entry_modified"] == "2024-07-24"
        assert result["entry_version"] == 275

    @pytest.mark.asyncio
    async def test_extract_sequence_modified_date(self, transformer, mock_context):
        """Test extraction of sequence modification date."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "sequence": {
                "value": "MSDV" * 120,
                "length": 480,
                "modified": "2007-01-23",
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["sequence_modified"] == "2007-01-23"

    @pytest.mark.asyncio
    async def test_missing_entry_audit(self, transformer, mock_context):
        """Test graceful handling when entryAudit is missing."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            # No entryAudit
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["entry_created"] is None
        assert result["entry_modified"] is None
        assert result["entry_version"] is None

    @pytest.mark.asyncio
    async def test_missing_sequence_modified(self, transformer, mock_context):
        """Test graceful handling when sequence modified date is missing."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "sequence": {
                "value": "MSDV" * 120,
                "length": 480,
                # No modified date
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["sequence_modified"] is None

    @pytest.mark.asyncio
    async def test_invalid_date_format_handled(self, transformer, mock_context):
        """Test that invalid date formats are handled gracefully."""
        record = {
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "entryAudit": {
                "firstPublicDate": "invalid-date",
                "lastAnnotationUpdateDate": "2024/07/24",  # Wrong format
                "entryVersion": 275,
            },
            "sequence": {
                "value": "MSDV" * 120,
                "length": 480,
                "modified": "not-a-date",
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["entry_created"] is None
        assert result["entry_modified"] is None
        assert result["sequence_modified"] is None
        # entry_version should still be extracted
        assert result["entry_version"] == 275

    @pytest.mark.asyncio
    async def test_full_record_with_audit_dates(self, transformer, mock_context):
        """Test complete transformation including audit metadata."""
        record = {
            "entryType": "UniProtKB reviewed (Swiss-Prot)",
            "primaryAccession": "P31749",
            "uniProtkbId": "AKT1_HUMAN",
            "entryAudit": {
                "firstPublicDate": "2000-12-01",
                "lastAnnotationUpdateDate": "2024-07-24",
                "entryVersion": 275,
                "sequenceVersion": 2,
            },
            "sequence": {
                "value": "MSDV" * 120,
                "length": 480,
                "molWeight": 55686,
                "modified": "2007-01-23",
            },
            "proteinDescription": {
                "recommendedName": {
                    "fullName": {"value": "RAC-alpha serine/threonine-protein kinase"}
                }
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        # Core fields
        assert result["accession"] == "P31749"
        assert result["entry_name"] == "AKT1_HUMAN"
        assert result["protein_name"] == "RAC-alpha serine/threonine-protein kinase"
        # Audit metadata
        assert result["entry_created"] == "2000-12-01"
        assert result["entry_modified"] == "2024-07-24"
        assert result["entry_version"] == 275
        assert result["sequence_modified"] == "2007-01-23"
        # Sequence data
        assert result["sequence_length"] == 480
        assert result["sequence_mass"] == 55686


@pytest.mark.unit
class TestUniProtCofactorsExtraction:
    """Tests for cofactor extraction."""

    @pytest.fixture
    def transformer(self):
        """Create UniProtProteinTransformer instance."""
        return _build_transformer(provider="uniprot")

    @pytest.mark.asyncio
    async def test_extract_cofactors_with_chebi(self, transformer, mock_context):
        """Test extraction of cofactors with ChEBI cross-references."""
        record = {
            "primaryAccession": "P12345",
            "uniProtkbId": "TEST_HUMAN",
            "comments": [
                {
                    "commentType": "COFACTOR",
                    "cofactors": [
                        {
                            "name": "Zn(2+)",
                            "cofactorCrossReference": {
                                "database": "ChEBI",
                                "id": "CHEBI:29105",
                            },
                        },
                        {
                            "name": "Mg(2+)",
                            "cofactorCrossReference": {
                                "database": "ChEBI",
                                "id": "CHEBI:18420",
                            },
                        },
                    ],
                }
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["cofactors"] is not None
        assert '"name":"Zn(2+)"' in result["cofactors"]
        assert '"chebi_id":"CHEBI:29105"' in result["cofactors"]
        assert '"name":"Mg(2+)"' in result["cofactors"]
        assert '"chebi_id":"CHEBI:18420"' in result["cofactors"]

    @pytest.mark.asyncio
    async def test_extract_cofactors_without_chebi(self, transformer, mock_context):
        """Test extraction of cofactors without ChEBI cross-references."""
        record = {
            "primaryAccession": "P12345",
            "uniProtkbId": "TEST_HUMAN",
            "comments": [
                {
                    "commentType": "COFACTOR",
                    "cofactors": [
                        {"name": "NAD(+)"},
                    ],
                }
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["cofactors"] is not None
        assert '"name":"NAD(+)"' in result["cofactors"]

    @pytest.mark.asyncio
    async def test_no_cofactors(self, transformer, mock_context):
        """Test handling when no cofactors are present."""
        record = {
            "primaryAccession": "P12345",
            "uniProtkbId": "TEST_HUMAN",
            "comments": [
                {
                    "commentType": "FUNCTION",
                    "texts": [{"value": "Some function"}],
                }
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["cofactors"] is None


@pytest.mark.unit
class TestUniProtBiophysicochemicalExtraction:
    """Tests for biophysicochemical properties extraction."""

    @pytest.fixture
    def transformer(self):
        """Create UniProtProteinTransformer instance."""
        return _build_transformer(provider="uniprot")

    @pytest.mark.asyncio
    async def test_extract_ph_dependence(self, transformer, mock_context):
        """Test extraction of pH dependence."""
        record = {
            "primaryAccession": "P12345",
            "uniProtkbId": "TEST_HUMAN",
            "comments": [
                {
                    "commentType": "BIOPHYSICOCHEMICAL PROPERTIES",
                    "phDependence": {
                        "texts": [
                            {"value": "Optimum pH is 7.5. Active from pH 6.0 to 9.0."}
                        ]
                    },
                }
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["biophysicochemical_properties"] is not None
        assert '"ph_dependence"' in result["biophysicochemical_properties"]
        assert "Optimum pH is 7.5" in result["biophysicochemical_properties"]

    @pytest.mark.asyncio
    async def test_extract_temperature_dependence(self, transformer, mock_context):
        """Test extraction of temperature dependence."""
        record = {
            "primaryAccession": "P12345",
            "uniProtkbId": "TEST_HUMAN",
            "comments": [
                {
                    "commentType": "BIOPHYSICOCHEMICAL PROPERTIES",
                    "temperatureDependence": {
                        "texts": [
                            {"value": "Optimum temperature is 37 degrees Celsius."}
                        ]
                    },
                }
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["biophysicochemical_properties"] is not None
        assert '"temperature_dependence"' in result["biophysicochemical_properties"]
        assert "37 degrees" in result["biophysicochemical_properties"]

    @pytest.mark.asyncio
    async def test_extract_kinetic_parameters(self, transformer, mock_context):
        """Test extraction of kinetic parameters (Km, Vmax)."""
        record = {
            "primaryAccession": "P12345",
            "uniProtkbId": "TEST_HUMAN",
            "comments": [
                {
                    "commentType": "BIOPHYSICOCHEMICAL PROPERTIES",
                    "kineticParameters": {
                        "michaelisConstants": [
                            {
                                "constant": 0.5,
                                "unit": "mM",
                                "substrate": "ATP",
                            }
                        ],
                        "maximumVelocities": [
                            {
                                "velocity": 100,
                                "unit": "umol/min/mg",
                                "enzyme": "recombinant enzyme",
                            }
                        ],
                    },
                }
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["biophysicochemical_properties"] is not None
        props = result["biophysicochemical_properties"]
        assert '"kinetic_parameters"' in props
        assert '"km"' in props
        assert '"vmax"' in props
        assert '"substrate":"ATP"' in props

    @pytest.mark.asyncio
    async def test_extract_redox_potential(self, transformer, mock_context):
        """Test extraction of redox potential."""
        record = {
            "primaryAccession": "P12345",
            "uniProtkbId": "TEST_HUMAN",
            "comments": [
                {
                    "commentType": "BIOPHYSICOCHEMICAL PROPERTIES",
                    "redoxPotential": {
                        "texts": [{"value": "E(0) is -320 mV at pH 7.0."}]
                    },
                }
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["biophysicochemical_properties"] is not None
        assert '"redox_potential"' in result["biophysicochemical_properties"]
        assert "-320 mV" in result["biophysicochemical_properties"]

    @pytest.mark.asyncio
    async def test_no_biophysicochemical_properties(self, transformer, mock_context):
        """Test handling when no biophysicochemical properties are present."""
        record = {
            "primaryAccession": "P12345",
            "uniProtkbId": "TEST_HUMAN",
            "comments": [
                {
                    "commentType": "FUNCTION",
                    "texts": [{"value": "Some function"}],
                }
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["biophysicochemical_properties"] is None


@pytest.mark.unit
class TestUniProtInductionExtraction:
    """Tests for induction extraction."""

    @pytest.fixture
    def transformer(self):
        """Create UniProtProteinTransformer instance."""
        return _build_transformer(provider="uniprot")

    @pytest.mark.asyncio
    async def test_extract_induction(self, transformer, mock_context):
        """Test extraction of induction information."""
        record = {
            "primaryAccession": "P12345",
            "uniProtkbId": "TEST_HUMAN",
            "comments": [
                {
                    "commentType": "INDUCTION",
                    "texts": [{"value": "Induced by heat shock and oxidative stress."}],
                }
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["induction"] is not None
        assert "Induced by heat shock" in result["induction"]

    @pytest.mark.asyncio
    async def test_no_induction(self, transformer, mock_context):
        """Test handling when no induction information is present."""
        record = {
            "primaryAccession": "P12345",
            "uniProtkbId": "TEST_HUMAN",
            "comments": [
                {
                    "commentType": "FUNCTION",
                    "texts": [{"value": "Some function"}],
                }
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["induction"] is None


@pytest.mark.unit
class TestUniProtPDBExtraction:
    """Tests for PDB cross-reference extraction."""

    @pytest.fixture
    def transformer(self):
        """Create UniProtProteinTransformer instance."""
        return _build_transformer(provider="uniprot")

    @pytest.mark.asyncio
    async def test_extract_pdb_xrefs(self, transformer, mock_context):
        """Test extraction of PDB cross-references."""
        record = {
            "primaryAccession": "P12345",
            "uniProtkbId": "TEST_HUMAN",
            "uniProtKBCrossReferences": [
                {
                    "database": "PDB",
                    "id": "1ABC",
                    "properties": [
                        {"key": "Method", "value": "X-ray"},
                        {"key": "Resolution", "value": "2.10 A"},
                        {"key": "Chains", "value": "A/B=1-480"},
                    ],
                },
                {
                    "database": "PDB",
                    "id": "2XYZ",
                    "properties": [
                        {"key": "Method", "value": "NMR"},
                        {"key": "Chains", "value": "A=1-150"},
                    ],
                },
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["pdb_xrefs"] is not None
        assert '"id":"1ABC"' in result["pdb_xrefs"]
        assert '"method":"X-ray"' in result["pdb_xrefs"]
        assert '"resolution":"2.10 A"' in result["pdb_xrefs"]
        assert '"chains":"A/B=1-480"' in result["pdb_xrefs"]
        assert '"id":"2XYZ"' in result["pdb_xrefs"]
        assert '"method":"NMR"' in result["pdb_xrefs"]

    @pytest.mark.asyncio
    async def test_extract_pdb_xrefs_minimal(self, transformer, mock_context):
        """Test extraction of PDB cross-references with minimal info."""
        record = {
            "primaryAccession": "P12345",
            "uniProtkbId": "TEST_HUMAN",
            "uniProtKBCrossReferences": [
                {
                    "database": "PDB",
                    "id": "1ABC",
                },
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["pdb_xrefs"] is not None
        assert '"id":"1ABC"' in result["pdb_xrefs"]

    @pytest.mark.asyncio
    async def test_no_pdb_xrefs(self, transformer, mock_context):
        """Test handling when no PDB cross-references are present."""
        record = {
            "primaryAccession": "P12345",
            "uniProtkbId": "TEST_HUMAN",
            "uniProtKBCrossReferences": [
                {"database": "GO", "id": "GO:0005524"},
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["pdb_xrefs"] is None


@pytest.mark.unit
class TestParseUniprotDate:
    """Tests for parse_uniprot_date utility function."""

    def test_valid_date(self):
        """Test parsing of valid ISO date string."""
        from datetime import date

        from bioetl.application.pipelines.uniprot.extractors import ExtractorHelper

        result = ExtractorHelper.parse_uniprot_date("2024-07-24")
        assert result == date(2024, 7, 24)

    def test_valid_date_beginning_of_year(self):
        """Test parsing date at beginning of year."""
        from datetime import date

        from bioetl.application.pipelines.uniprot.extractors import ExtractorHelper

        result = ExtractorHelper.parse_uniprot_date("2000-01-01")
        assert result == date(2000, 1, 1)

    def test_valid_date_end_of_year(self):
        """Test parsing date at end of year."""
        from datetime import date

        from bioetl.application.pipelines.uniprot.extractors import ExtractorHelper

        result = ExtractorHelper.parse_uniprot_date("1999-12-31")
        assert result == date(1999, 12, 31)

    def test_none_input(self):
        """Test that None input returns None."""
        from bioetl.application.pipelines.uniprot.extractors import ExtractorHelper

        result = ExtractorHelper.parse_uniprot_date(None)
        assert result is None

    def test_parse_uniprot_date__empty_string__1281210c(self):
        """Test that empty string returns None."""
        from bioetl.application.pipelines.uniprot.extractors import ExtractorHelper

        result = ExtractorHelper.parse_uniprot_date("")
        assert result is None

    def test_invalid_format_slash(self):
        """Test that slash-separated date returns None."""
        from bioetl.application.pipelines.uniprot.extractors import ExtractorHelper

        result = ExtractorHelper.parse_uniprot_date("2024/07/24")
        assert result is None

    def test_invalid_format_text(self):
        """Test that text date returns None."""
        from bioetl.application.pipelines.uniprot.extractors import ExtractorHelper

        result = ExtractorHelper.parse_uniprot_date("July 24, 2024")
        assert result is None

    def test_invalid_date_values(self):
        """Test that invalid date values return None."""
        from bioetl.application.pipelines.uniprot.extractors import ExtractorHelper

        result = ExtractorHelper.parse_uniprot_date("2024-13-01")  # Invalid month
        assert result is None

        result = ExtractorHelper.parse_uniprot_date("2024-02-30")  # Invalid day
        assert result is None

    def test_non_string_input(self):
        """Test that non-string input returns None."""
        from bioetl.application.pipelines.uniprot.extractors import ExtractorHelper

        result = ExtractorHelper.parse_uniprot_date(12345)
        assert result is None

        result = ExtractorHelper.parse_uniprot_date(["2024-07-24"])
        assert result is None

        result = ExtractorHelper.parse_uniprot_date({"date": "2024-07-24"})
        assert result is None
