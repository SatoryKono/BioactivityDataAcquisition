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
"""Unit tests for deterministic sort policy in pipeline sink schema."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

pytestmark = pytest.mark.unit


def _base_payload() -> dict[str, object]:
    return {
        "pipeline_name": "demo_item",
        "provider": "demo",
        "entity_type": "item",
        "business_primary_keys": ["id"],
        "technical_primary_key": "entity_id",
    }


def test_pipeline_schema_requires_sort_by_for_enabled_silver_gold_layers() -> None:
    payload = {
        **_base_payload(),
        "sink": {
            "silver": {"enabled": True, "mode": "merge"},
            "gold": {"enabled": True, "mode": "append"},
        },
    }

    with pytest.raises(
        ValidationError,
        match="sink\\.silver\\.sort_by must be configured for deterministic output",
    ):
        PipelineYamlConfig.model_validate(payload)


def test_pipeline_schema_accepts_valid_sort_by_policy() -> None:
    payload = {
        **_base_payload(),
        "sink": {
            "silver": {"enabled": True, "sort_by": [" entity_id ", "id"]},
            "gold": {"enabled": True, "sort_by": ["entity_id", "id"]},
        },
    }

    config = PipelineYamlConfig.model_validate(payload)
    assert config.sink["silver"].sort_by == ["entity_id", "id"]
    assert config.sink["gold"].sort_by == ["entity_id", "id"]
