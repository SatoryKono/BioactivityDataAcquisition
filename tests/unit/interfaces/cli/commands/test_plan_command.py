# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Unit tests for maintenance plan CLI command."""

from __future__ import annotations

import json
from typing import Any

import pytest
from click.testing import CliRunner

from bioetl.application.services.contract.contract_migration_service import (
    ContractMigrationAction,
    ContractMigrationPlan,
    ContractVersionTransition,
)
from bioetl.interfaces.cli.main import cli


class _FakeContractMigrationService:
    def plan_pipeline(self, pipeline_name: str) -> ContractMigrationPlan:
        assert pipeline_name == "chembl_activity"
        return ContractMigrationPlan(
            pipeline_name="chembl_activity",
            provider="chembl",
            entity_type="activity",
            contract_ref="chembl.activity",
            active_version="1.0.0",
            rollout_mode="dual_read_write",
            read_order=("1.0.0", "2.0.0"),
            write_versions=("1.0.0", "2.0.0"),
            shadow_versions=("2.0.0",),
            affects_hash=True,
            supported_versions=("1.0.0", "2.0.0"),
            transitions=(
                ContractVersionTransition(
                    from_version="1.0.0",
                    to_version="2.0.0",
                    migration_guide="docs/migrations/chembl-activity-v2.md",
                    affects_hash=True,
                ),
            ),
            required_actions=(
                ContractMigrationAction(
                    code="silver_backfill_rebuild",
                    title="Silver backfill/rebuild",
                    description="Rebuild Silver first.",
                ),
                ContractMigrationAction(
                    code="gold_backfill_rebuild",
                    title="Gold backfill/rebuild",
                    description="Rebuild Gold second.",
                ),
                ContractMigrationAction(
                    code="verification_before_cutover",
                    title="Verification before cutover",
                    description="Verify before promoting.",
                ),
            ),
            notes=("Rollback remains possible.",),
        )


@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()


def _patch_contract_migration_service(monkeypatch: Any, service: object) -> None:
    import bioetl.interfaces.cli.commands.domains.maintenance.plan as plan_cmd

    monkeypatch.setattr(
        plan_cmd,
        "get_contract_migration_service",
        lambda: service,
        raising=True,
    )


@pytest.mark.unit
class TestPlanCommand:
    def test_plan_help_displays_options(self, cli_runner: CliRunner) -> None:
        result = cli_runner.invoke(cli, ["maintenance", "plan", "--help"])

        assert result.exit_code == 0
        assert "PIPELINE" in result.output
        assert "--format" in result.output

    def test_plan_text_renders_required_actions(
        self,
        cli_runner: CliRunner,
        monkeypatch: Any,
    ) -> None:
        _patch_contract_migration_service(monkeypatch, _FakeContractMigrationService())

        result = cli_runner.invoke(cli, ["maintenance", "plan", "chembl_activity"])

        assert result.exit_code == 0
        assert "Contract Migration Plan" in result.output
        assert "Required Actions" in result.output
        assert "Silver backfill/rebuild" in result.output
        assert "Verification before cutover" in result.output

    def test_plan_json_renders_payload(
        self,
        cli_runner: CliRunner,
        monkeypatch: Any,
    ) -> None:
        _patch_contract_migration_service(monkeypatch, _FakeContractMigrationService())

        result = cli_runner.invoke(
            cli,
            ["maintenance", "plan", "chembl_activity", "--format", "json"],
        )

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["pipeline_name"] == "chembl_activity"
        assert payload["required_actions"][0]["code"] == "silver_backfill_rebuild"
