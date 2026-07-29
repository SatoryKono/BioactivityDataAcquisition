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
"""Unit tests for canonical contract policy validation helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.infrastructure.config.contract_policy_validation import (
    validate_contract_policy_registry_alignment,
    resolve_silver_columns,
    schema_columns,
    validate_pipeline_contract_policy,
)
from bioetl.infrastructure.schemas.pipeline_contract_policy import (
    PipelineContractPolicy,
)


@pytest.mark.unit
def test_schema_columns_extracts_column_names() -> None:
    schema_cls = MagicMock()
    resolved = MagicMock()
    resolved.columns = {"col_a": MagicMock(), "col_b": MagicMock()}
    schema_cls.to_schema.return_value = resolved

    result = schema_columns(schema_cls)

    assert result == {"col_a", "col_b"}


@pytest.mark.unit
def test_schema_columns_prefers_pandera_fields_fast_path() -> None:
    schema_cls = SimpleNamespace(
        __fields__={"field_a": object(), "_aliased_b": object()},
    )

    result = schema_columns(schema_cls)

    assert result == {"field_a", "_aliased_b"}


@pytest.mark.unit
def test_schema_columns_raises_when_schema_has_no_to_schema() -> None:
    with pytest.raises(ValueError, match="does not expose to_schema"):
        schema_columns(SimpleNamespace())


@pytest.mark.unit
def test_resolve_silver_columns_prefers_pandera_schema() -> None:
    pandera_schema = MagicMock()
    resolved = MagicMock()
    resolved.columns = {"x": MagicMock()}
    pandera_schema.to_schema.return_value = resolved

    result = resolve_silver_columns(
        provider="test",
        entity_type="entity",
        pandera_silver_schema=pandera_schema,
        silver_schema=MagicMock(),
    )

    assert result == {"x"}


@pytest.mark.unit
def test_validate_pipeline_contract_policy_raises_when_keys_missing() -> None:
    pandera_schema = MagicMock()
    pandera_resolved = MagicMock()
    pandera_resolved.columns = {"pk": MagicMock()}
    pandera_schema.to_schema.return_value = pandera_resolved

    gold_schema = MagicMock()
    gold_resolved = MagicMock()
    gold_resolved.columns = {"pk": MagicMock()}
    gold_schema.to_schema.return_value = gold_resolved

    with pytest.raises(ValueError, match="Invalid contract policy"):
        validate_pipeline_contract_policy(
            provider="test",
            entity_type="entity",
            pandera_silver_schema=pandera_schema,
            silver_schema=None,
            gold_schema=gold_schema,
            load_policy=lambda _provider, _entity: SimpleNamespace(
                primary_key=["pk", "missing_key"],
                merge_keys=[],
            ),
        )


@pytest.mark.unit
def test_validate_contract_policy_registry_alignment_requires_guide_for_major_transition() -> (
    None
):
    policy = PipelineContractPolicy.model_validate(
        {
            "primary_key": ["id"],
            "merge_keys": ["id"],
            "contract_ref": "chembl.activity",
            "active_version": "2.0.0",
            "rollout": {
                "mode": "dual_read_write",
                "read_order": ["2.0.0", "1.0.0"],
                "write_versions": ["1.0.0", "2.0.0"],
                "affects_hash": True,
            },
        }
    )

    with pytest.raises(ValueError, match="Missing migration guide"):
        validate_contract_policy_registry_alignment(
            policy,
            registry_entries={
                "chembl.activity": {
                    "supported_versions": ["1.0.0", "2.0.0"],
                    "migration_guides": {},
                }
            },
        )
