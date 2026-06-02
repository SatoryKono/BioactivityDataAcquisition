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
