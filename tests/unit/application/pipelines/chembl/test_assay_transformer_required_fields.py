"""Config-driven required-field regressions for ChEMBL assay transformer."""

from __future__ import annotations

import dataclasses
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.base_transformer import FilteredOutError
from bioetl.application.core.base_transformer.structural_policy import (
    build_structural_policy,
)
from bioetl.application.pipelines.chembl.assay_transformer import AssayTransformer
from bioetl.domain.context import PipelineContext
from bioetl.domain.schemas.chembl.assay import AssaySchema
from bioetl.domain.types import RunType
from bioetl.infrastructure.config.domain_config_resolver import (
    resolve_domain_pipeline_config,
)
from bioetl.infrastructure.config.pipeline_config_loader import PipelineConfigLoader
from tests.helpers.transformer_dependencies import build_test_transformer_dependencies


@pytest.fixture
def mock_context() -> PipelineContext:
    """Create a mock pipeline context."""
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    mock_logger.warning = MagicMock()
    return PipelineContext(
        run_id=uuid4(),
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )


def _valid_contract_record() -> dict[str, object]:
    """Build a valid chembl_assay record under current config filters."""
    return {
        "assay_id": "CHEMBL1234567",
        "description": "Binding assay",
        "assay_type": "B",
        "assay_type_description": "Binding",
        "target_id": "CHEMBL1862",
        "publication_id": "CHEMBL456",
        "bao_format": "BAO_0000218",
        "relationship_type": "D",
        "confidence_score": 9,
        "src_id": 1,
    }


@pytest.mark.unit
class TestAssayTransformerRequiredFields:
    """Required-field regressions for chembl_assay runtime policy."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("missing_field",),
        (
            ("publication_id",),
            ("bao_format",),
            ("assay_type_description",),
            ("relationship_type",),
            ("confidence_score",),
        ),
    )
    async def test_required_fields__missing_fields__9fe7cb24(
        self,
        mock_context: PipelineContext,
        missing_field: str,
    ) -> None:
        """chembl_assay config should quarantine schema-required missing fields."""
        loader = PipelineConfigLoader(Path("configs"))
        yaml_config = loader.load_pipeline_config("chembl_assay")
        domain_config = resolve_domain_pipeline_config(yaml_config)
        dependencies = dataclasses.replace(
            build_test_transformer_dependencies(),
            structural_policy=build_structural_policy(
                domain_config=domain_config,
                pandera_silver_schema=AssaySchema,
            ),
        )
        transformer = AssayTransformer(
            provider="chembl",
            silver_filters=domain_config.silver_filters,
            gold_filters=domain_config.gold_filters,
            dependencies=dependencies,
        )

        record = _valid_contract_record()
        record.pop(missing_field)

        transformed = await transformer._transform_impl(mock_context, record, 0)

        with pytest.raises(FilteredOutError) as exc_info:
            structured = transformer._apply_structural_policy(
                mock_context, transformed, 0
            )
            transformer._apply_silver_filter(mock_context, structured, 0)

        details = exc_info.value.details
        assert details["policy_stage"] == "structural"
        assert details["reason_code"] == "required_field_missing"
        assert details["field"] == missing_field
        assert details["optional_sources"] == ["silver_required_fields"]
        assert details["silver_filter_shadow_reason_code"] == "required_field_missing"
