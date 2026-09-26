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
"""Direct unit tests for DQ report orchestration models."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from bioetl.application.services.quality.dq_report_models import (
    DQReportContext,
    DQReportResult,
)
from bioetl.domain.types import GoldBusinessRuleSpec, ScdConfig

BRONZE_REPORT_PATH = Path("reports/bronze.json")
GOLD_REPORT_PATH = Path("reports/gold.json")


@pytest.mark.unit
class TestDQReportResult:
    def test_properties_reflect_generated_report_paths(self) -> None:
        result = DQReportResult(
            bronze_report_path=BRONZE_REPORT_PATH,
            gold_report_path=GOLD_REPORT_PATH,
            bronze_enabled=True,
            gold_enabled=True,
        )

        assert result.any_generated is True
        assert result.reports_count == 2

    def test_properties_return_zero_when_no_reports_exist(self) -> None:
        result = DQReportResult()

        assert result.any_generated is False
        assert result.reports_count == 0


@pytest.mark.unit
class TestDQReportContext:
    def test_post_init_coerces_business_rules_and_scd_mappings(self) -> None:
        context = DQReportContext(
            run_id="run-001",
            pipeline_name="chembl_activity",
            timestamp=datetime(2026, 3, 19, 12, 0, tzinfo=UTC),
            gold_business_rules=[
                {
                    "rule_id": "R-1",
                    "column": "activity_id",
                    "condition": "not_null",
                }
            ],
            gold_scd_config={"entity_key": "activity_id", "type": 2},
        )

        assert context.gold_business_rules is not None
        assert isinstance(context.gold_business_rules[0], GoldBusinessRuleSpec)
        assert context.gold_business_rules[0].rule_id == "R-1"
        assert isinstance(context.gold_scd_config, ScdConfig)
        assert context.gold_scd_config.entity_key == "activity_id"

    def test_post_init_preserves_typed_inputs(self) -> None:
        rule = GoldBusinessRuleSpec(column="activity_id", condition="not_null")
        scd_config = ScdConfig(business_key="activity_id")

        context = DQReportContext(
            run_id="run-002",
            pipeline_name="chembl_activity",
            timestamp=datetime(2026, 3, 19, 12, 30, tzinfo=UTC),
            gold_business_rules=[rule],
            gold_scd_config=scd_config,
        )

        assert context.gold_business_rules == [rule]
        assert context.gold_scd_config is scd_config
