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
"""Unit tests for pipeline config_types contracts."""

from __future__ import annotations

import pytest

from bioetl.composition.factories.pipeline.config_types import PipelineFactoryConfig


class _DummyTransformer:
    """Minimal transformer stand-in for config assembly tests."""


@pytest.mark.unit
class TestPipelineFactoryConfig:
    """Contract-level tests for PipelineFactoryConfig."""

    def test_exposes_required_registration_shape(self) -> None:
        """Config stores canonical registration fields in stable order."""
        config = PipelineFactoryConfig(
            pipeline_name="chembl_activity",
            provider="chembl",
            entity_type="activity",
            transformer_class=_DummyTransformer,
            silver_schema=None,
            gold_schema=object(),
        )

        assert config.pipeline_name == "chembl_activity"
        assert config.provider == "chembl"
        assert config.entity_type == "activity"
        assert config.transformer_class is _DummyTransformer
        assert config.silver_schema is None
        assert config._fields[:6] == (
            "pipeline_name",
            "provider",
            "entity_type",
            "transformer_class",
            "silver_schema",
            "gold_schema",
        )

    def test_optional_registration_fields_default_to_none(self) -> None:
        """Optional config wiring defaults remain non-eager and explicit."""
        config = PipelineFactoryConfig(
            pipeline_name="pubmed_publication",
            provider="pubmed",
            entity_type="publication",
            transformer_class=_DummyTransformer,
            silver_schema=None,
            gold_schema=object(),
        )

        assert config.pandera_silver_schema is None
        assert config.data_source_provider is None
