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
"""Unit tests for record-processor helper seams extracted from pipeline_builder."""

from __future__ import annotations

import pytest

from tests.helpers.synthetic_paths import synthetic_test_root
from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock

from bioetl.application.core.wiring.runtime import BasePipeline
from bioetl.composition.bootstrap_contexts import PipelineCallbacksContext
from bioetl.composition.factories.services.pipeline_record_processor_builder import (
    build_record_processor_config_and_validator,
    create_record_processor_from_pipeline,
)

pytestmark = pytest.mark.unit

TEST_ROOT = synthetic_test_root("bioetl-record-processor-builder")
BRONZE_ROOT = str(TEST_ROOT / "bronze")
SILVER_ROOT = str(TEST_ROOT / "silver")
GOLD_ROOT = str(TEST_ROOT / "gold")


def _make_pipeline() -> BasePipeline:
    pipeline = MagicMock()
    pipeline.services = MagicMock(name="services")
    pipeline.context = MagicMock(name="context")
    pipeline.transformer = SimpleNamespace(
        _identity=SimpleNamespace(
            _content_hash_include_fields={"doi", "title"},
            _content_hash_exclude_fields={"journal"},
        ),
        _contract_policy=SimpleNamespace(
            active_version="2.0.0",
            hash_include=("doi", "publication_date"),
            hash_exclude=("publisher",),
            hash_datetime_policy="v2_datetime_utc",
            rollout=SimpleNamespace(
                write_versions=("1.0.0", "2.0.0"),
                affects_hash=True,
            ),
        ),
    )
    pipeline.config.pipeline_name = "chembl_activity"
    pipeline.config.provider = "chembl"
    pipeline.config.entity_type = "activity"
    pipeline.config.dq = None
    pipeline.config.table = MagicMock()
    pipeline.config.table.primary_keys = ["pk"]
    pipeline.config.effective_silver_table = "silver_table"
    pipeline.config.effective_gold_table = "gold_table"
    pipeline.config.table.silver_write_mode = "merge"
    pipeline.config.table.gold_write_mode = "overwrite"
    pipeline.config.table.on_schema_mismatch = "error"
    pipeline.config.column_groups = ["system", "business"]
    pipeline.config.scd_config = {"type": 2}
    return cast(BasePipeline, pipeline)


def _make_callbacks() -> PipelineCallbacksContext:
    return cast(
        PipelineCallbacksContext,
        SimpleNamespace(
            transform=MagicMock(name="transform"),
            gold_filter=MagicMock(name="gold_filter"),
            gold_transform=MagicMock(name="gold_transform"),
        ),
    )


def test_create_record_processor_from_pipeline_projects_pipeline_fields() -> None:
    pipeline = _make_pipeline()
    active_schema = MagicMock(name="active_gold_schema")
    shadow_schema = MagicMock(name="shadow_gold_schema")
    pipeline.gold_schema_by_version = {
        "1.0.0": shadow_schema,
        "2.0.0": active_schema,
    }
    callbacks = _make_callbacks()
    create_fn = MagicMock(return_value=MagicMock(name="record_processor"))

    create_record_processor_from_pipeline(
        pipeline=pipeline,
        silver_schema=None,
        gold_schema=active_schema,
        callbacks=callbacks,
        create_record_processor_fn=create_fn,
        lock_validator=MagicMock(name="lock_validator"),
        tracer=MagicMock(name="tracer"),
    )

    call_kwargs = create_fn.call_args.kwargs
    request = call_kwargs["request"]
    assert request.services is pipeline.services
    assert request.context is pipeline.context
    assert request.pipeline_name == "chembl_activity"
    assert request.provider == "chembl"
    assert request.entity_type == "activity"
    assert request.column_groups == ("system", "business")
    assert request.scd_config == {"type": 2}
    assert request.content_hash_policy_authoritative is True
    assert request.content_hash_include_fields == frozenset({"doi", "title"})
    assert request.content_hash_exclude_fields == frozenset(
        {"journal", "entity_id", "content_hash"}
    )
    assert request.content_hash_policy_by_version is not None
    assert request.content_hash_policy_by_version.active_version == "2.0.0"
    assert request.content_hash_policy_by_version.affects_hash is True
    assert request.content_hash_policy_by_version.versions == (
        "1.0.0",
        "2.0.0",
    )
    assert {
        policy.datetime_policy
        for policy in request.content_hash_policy_by_version.policies
    } == {"v2_datetime_utc"}
    assert request.gold_schema_policy_by_version is not None
    assert request.gold_schema_policy_by_version.active_schema is active_schema
    assert request.gold_schema_policy_by_version.for_version("1.0.0") is shadow_schema


def test_build_record_processor_config_and_validator_forwards_paths_and_strict() -> (
    None
):
    pipeline = _make_pipeline()
    active_schema = MagicMock(name="active_gold_schema")
    shadow_schema = MagicMock(name="shadow_gold_schema")
    pipeline.gold_schema_by_version = {
        "1.0.0": shadow_schema,
        "2.0.0": active_schema,
    }
    gold_validator_factory = MagicMock(return_value=MagicMock(name="validator"))

    config, validator = build_record_processor_config_and_validator(
        pipeline=pipeline,
        silver_schema=None,
        gold_schema=active_schema,
        strict_gold_validation=False,
        bronze_output_path=BRONZE_ROOT,
        silver_output_path=SILVER_ROOT,
        gold_output_path=GOLD_ROOT,
        flat_structure=True,
        gold_validator_factory=gold_validator_factory,
    )

    assert config.pipeline_name == "chembl_activity"
    assert config.bronze_output_path == BRONZE_ROOT
    assert config.silver_output_path == SILVER_ROOT
    assert config.gold_output_path == GOLD_ROOT
    assert config.flat_structure is True
    assert config.content_hash_policy_authoritative is True
    assert config.content_hash_include_fields == frozenset({"doi", "title"})
    assert config.content_hash_exclude_fields == frozenset(
        {"journal", "entity_id", "content_hash"}
    )
    assert config.allow_compatibility_fallback is False
    assert config.content_hash_policy_by_version is not None
    assert config.content_hash_policy_by_version.affects_hash is True
    assert config.content_hash_policy_by_version.versions == ("1.0.0", "2.0.0")
    assert {
        policy.datetime_policy
        for policy in config.content_hash_policy_by_version.policies
    } == {"v2_datetime_utc"}
    assert config.gold_schema_policy_by_version is not None
    assert config.gold_schema_policy_by_version.versions == ("1.0.0", "2.0.0")
    assert config.gold_schema_policy_by_version.active_schema is active_schema
    assert config.gold_schema_policy_by_version.for_version("1.0.0") is shadow_schema
    assert validator is gold_validator_factory.return_value
    assert gold_validator_factory.call_args.args[0] is active_schema
    assert gold_validator_factory.call_args.kwargs["strict"] is False


def test_build_record_processor_config_tracks_non_hash_affecting_rollout_versions() -> (
    None
):
    pipeline = _make_pipeline()
    pipeline.transformer._contract_policy.rollout = SimpleNamespace(
        write_versions=("1.0.0", "2.0.0"),
        affects_hash=False,
    )

    config, _validator = build_record_processor_config_and_validator(
        pipeline=pipeline,
        silver_schema=None,
        gold_schema=MagicMock(name="gold_schema"),
        strict_gold_validation=True,
        bronze_output_path=None,
        silver_output_path=None,
        gold_output_path=None,
        flat_structure=False,
        gold_validator_factory=MagicMock(return_value=MagicMock(name="validator")),
    )

    assert config.content_hash_policy_by_version is not None
    assert config.content_hash_policy_by_version.versions == ("1.0.0", "2.0.0")
    assert config.content_hash_policy_by_version.affects_hash is False
    assert config.content_hash_policy_by_version.requires_projected_hashes is False
