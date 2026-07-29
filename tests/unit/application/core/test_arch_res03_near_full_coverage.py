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
"""Close single-line coverage gaps for ARCH-RES-03 hotspot-core modules."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.application.core.base_transformer.field_policy import (
    _collect_explicit_field_policy,
)
from bioetl.application.core.base_transformer_runtime import normalize_lineage_value
from bioetl.application.core.runner_flow_metrics import _record_stage_lag_gauges

pytestmark = pytest.mark.unit


def test_collect_explicit_field_policy_skips_framework_managed_fields() -> None:
    policy = SimpleNamespace(field="_run_id")  # framework-managed name
    domain_config = SimpleNamespace(field_policy=(policy,))
    assert _collect_explicit_field_policy(domain_config) == {}


def test_collect_explicit_field_policy_skips_non_string_field_names() -> None:
    policy = SimpleNamespace(field=123)
    domain_config = SimpleNamespace(field_policy=(policy,))
    assert _collect_explicit_field_policy(domain_config) == {}


def test_normalize_lineage_value_passthrough_for_unhandled_fields() -> None:
    assert normalize_lineage_value(field_name="entity", value="chembl") == "chembl"


def test_record_stage_lag_gauges_uses_zero_when_started_at_missing() -> None:
    metrics = MagicMock()
    host = SimpleNamespace(_context=SimpleNamespace(started_at=None))
    _record_stage_lag_gauges(
        host=host,
        pipeline_metrics=metrics,
        run_type="full",
        ingestion_backlog=1,
        validation_backlog=0,
        output_backlog=0,
        current_time_fn=lambda: datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert metrics.record_stage_lag_seconds.called
