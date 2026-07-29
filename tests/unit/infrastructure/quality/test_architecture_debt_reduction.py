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
"""Unit tests for architecture debt reduction planning helpers."""

from __future__ import annotations

import pytest

from datetime import UTC
from datetime import datetime

from bioetl.infrastructure.quality.architecture_debt_reduction import (
    build_architecture_debt_execution_plan,
)


pytestmark = pytest.mark.unit


def test_build_execution_plan_classifies_and_orders_batches() -> None:
    payload = {
        "source_tasks_file": "tasks_architecture_metric_exemptions_2026-04-04-09-30.json",
        "tasks": [
            {
                "id": "AME-FILE-001",
                "registry": "file_size_limits",
                "status": "within_limit",
                "current_value": 200,
                "delta_to_limit": -20,
                "target_file": "src/bioetl/domain/module.py",
            },
            {
                "id": "AME-CPLX-001",
                "registry": "function_complexity",
                "status": "needs_refactor",
                "current_value": 8,
                "delta_to_limit": 3,
                "target_file": "src/bioetl/domain/rules.py",
            },
            {
                "id": "AME-MISSING-001",
                "registry": "class_size",
                "status": "target_not_found",
                "current_value": None,
                "delta_to_limit": None,
                "target_file": None,
            },
        ],
    }

    plan = build_architecture_debt_execution_plan(
        payload,
        generated_at=datetime(2026, 4, 4, 10, 0, tzinfo=UTC),
    )

    summary = plan["summary"]
    assert summary["total_tasks"] == 3
    assert summary["actionable_tasks"] == 2
    assert summary["category_counts"]["STALE_EXEMPTION"] == 1
    assert summary["category_counts"]["COMPLEXITY"] == 1
    assert summary["category_counts"]["TARGET_NOT_FOUND"] == 1

    batches = plan["batches"]
    assert batches[0]["category"] == "STALE_EXEMPTION"
    assert batches[1]["category"] == "COMPLEXITY"
    assert batches[2]["category"] == "TARGET_NOT_FOUND"
    assert batches[0]["primary_executor"] == "py-config-bot"
    assert "py-config-bot" in plan["tasks"][1]["supporting_agents"]


def test_build_execution_plan_classifies_artifact_tasks_before_exemption_tasks() -> (
    None
):
    payload = {
        "source_tasks_file": "tasks_architecture_metric_exemptions_2026-04-04-09-30.json",
        "tasks": [
            {
                "id": "ARD-COMPAT-001",
                "task_family": "compatibility_surface",
                "registry": "artifact_governance",
                "status": "needs_refactor",
                "current_value": 12,
                "delta_to_limit": 12,
                "target_file": None,
            },
            {
                "id": "ARD-DUP-001",
                "task_family": "duplication_cluster",
                "registry": "artifact_governance",
                "status": "needs_refactor",
                "current_value": 5,
                "delta_to_limit": 5,
                "target_file": "src/bioetl/interfaces/cli",
            },
            {
                "id": "ARD-HOT-001",
                "task_family": "hotspot_family",
                "registry": "artifact_governance",
                "status": "needs_refactor",
                "current_value": 2,
                "delta_to_limit": 2,
                "target_file": "src/bioetl/composition/bootstrap/runtime/",
            },
            {
                "id": "ARD-DEAD-001",
                "task_family": "dead_code_review",
                "registry": "artifact_governance",
                "status": "needs_refactor",
                "current_value": 10,
                "delta_to_limit": 10,
                "target_file": None,
            },
            {
                "id": "AME-CPLX-001",
                "registry": "function_complexity",
                "status": "needs_refactor",
                "current_value": 8,
                "delta_to_limit": 3,
                "target_file": "src/bioetl/domain/rules.py",
            },
        ],
    }

    plan = build_architecture_debt_execution_plan(
        payload,
        generated_at=datetime(2026, 4, 4, 10, 0, tzinfo=UTC),
    )

    summary = plan["summary"]
    assert summary["total_tasks"] == 5
    assert summary["actionable_tasks"] == 5
    assert summary["category_counts"]["COMPATIBILITY_DEBT"] == 1
    assert summary["category_counts"]["DUPLICATION"] == 1
    assert summary["category_counts"]["HOTSPOT_SIZE_COUPLING_DEBT"] == 1
    assert summary["category_counts"]["DEAD_CODE_REVIEW_DEBT"] == 1
    assert summary["category_counts"]["COMPLEXITY"] == 1
    assert plan["execution_order"][:4] == [
        "COMPATIBILITY_DEBT",
        "DUPLICATION",
        "HOTSPOT_SIZE_COUPLING_DEBT",
        "DEAD_CODE_REVIEW_DEBT",
    ]
    assert [batch["category"] for batch in plan["batches"][:4]] == [
        "COMPATIBILITY_DEBT",
        "DUPLICATION",
        "HOTSPOT_SIZE_COUPLING_DEBT",
        "DEAD_CODE_REVIEW_DEBT",
    ]
