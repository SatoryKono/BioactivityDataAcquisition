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
"""Fail-closed residuals for #8957 CLI leftovers (not #8910/#8911)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bioetl.interfaces.cli.commands._run_manifest_historical_support import (
    _coerce_universe_external_record,
)
from bioetl.interfaces.cli.commands._workflow_override_support import (
    build_workflow_run_options_override_from_mapping,
)
from bioetl.interfaces.cli.commands.debug import _run_debug_session
from bioetl.interfaces.cli.commands.domains.diagnostics.contract_checks import (
    run_observability_contract_checks,
)
from bioetl.interfaces.cli.commands.domains.run_all.command_policy import (
    run_all_command_flow,
)
from bioetl.interfaces.cli.commands.lineage import _resolve_explain_identifier
from bioetl.interfaces.cli.commands.quarantine import quarantine_serve
from tests.unit.interfaces.cli.commands.test_run_all_command_policy import (
    _make_cli_input,
    _make_plan,
)

pytestmark = pytest.mark.unit


class TestWorkflowOverrideParsing:
    def test_bool_is_not_accepted_as_int(self) -> None:
        cfg = build_workflow_run_options_override_from_mapping(
            {"limit": True, "start_offset": False}
        )
        assert cfg.limit is None
        assert cfg.start_offset is None

    def test_dry_run_uses_optional_bool(self) -> None:
        assert (
            build_workflow_run_options_override_from_mapping({"dry_run": True}).dry_run
            is True
        )
        assert (
            build_workflow_run_options_override_from_mapping({"dry_run": False}).dry_run
            is False
        )
        assert (
            build_workflow_run_options_override_from_mapping({"dry_run": "yes"}).dry_run
            is None
        )


class TestHistoricalDurableEvidenceCoverage:
    def test_non_boolean_coverage_is_rejected(self) -> None:
        payload = {
            "manifest_id": "m1",
            "run_id": "r1",
            "pipeline_name": "chembl_activity",
            "provider": "chembl",
            "entity": "activity",
            "execution_context": "historical",
            "certification_status": "already_certified",
            "replay_occurrence_kind": "historical_source_replay",
            "durable_evidence_coverage": 1,
        }
        with pytest.raises(ValueError, match="durable_evidence_coverage"):
            _coerce_universe_external_record(payload, pack_ref="pack-1")

    def test_real_json_boolean_is_accepted(self) -> None:
        payload = {
            "manifest_id": "m1",
            "run_id": "r1",
            "pipeline_name": "chembl_activity",
            "provider": "chembl",
            "entity": "activity",
            "execution_context": "historical",
            "certification_status": "already_certified",
            "replay_occurrence_kind": "historical_source_replay",
            "durable_evidence_coverage": True,
        }
        record = _coerce_universe_external_record(payload, pack_ref="pack-1")
        assert record.durable_evidence_coverage is True


class TestDebugFailFast:
    @pytest.mark.asyncio
    async def test_unsupported_mode_raises_before_run(self) -> None:
        with patch(
            "bioetl.interfaces.cli.commands.debug.get_pipeline_runner_service"
        ) as get_service:
            with pytest.raises(ValueError, match="Unsupported debug mode"):
                await _run_debug_session(
                    pipeline="chembl_activity",
                    options=MagicMock(),
                    mode="interactive",
                    enabled_breakpoints=None,
                )
            get_service.assert_not_called()

    @pytest.mark.asyncio
    async def test_breakpoints_raise_before_run(self) -> None:
        with patch(
            "bioetl.interfaces.cli.commands.debug.get_pipeline_runner_service"
        ) as get_service:
            with pytest.raises(ValueError, match="Unsupported debug mode"):
                await _run_debug_session(
                    pipeline="chembl_activity",
                    options=MagicMock(),
                    mode="log",
                    enabled_breakpoints={"after_preflight"},
                )
            get_service.assert_not_called()


class TestRunAllDestructiveConfirmation:
    def test_false_confirmation_returns_without_execution(self) -> None:
        plan = _make_plan()
        execute_batch = MagicMock()
        preview_emitter = MagicMock()
        with patch(
            "bioetl.interfaces.cli.commands.domains.run_all.command_policy.prepare_run_all_execution_plan",
            return_value=plan,
        ):
            run_all_command_flow(
                cli_input=_make_cli_input(),
                registry=MagicMock(),
                destructive_confirmation=MagicMock(return_value=False),
                listing_emitter=MagicMock(),
                preview_emitter=preview_emitter,
                health_info_presenter=MagicMock(),
                execute_batch=execute_batch,
                summary_presenter=MagicMock(),
                determine_exit_code=MagicMock(),
                exit_func=MagicMock(),
            )
        preview_emitter.assert_not_called()
        execute_batch.assert_not_called()


class TestContractChecksDoNotPropagateYamlErrors:
    def test_invalid_yaml_returns_failed_check(self, tmp_path: Path) -> None:
        (tmp_path / "configs/quality").mkdir(parents=True)
        (tmp_path / "grafana/prometheus-rules").mkdir(parents=True)
        (
            tmp_path / "configs/quality/observability_metric_inventory_allowlist.yaml"
        ).write_text(
            ":\n  - [",
            encoding="utf-8",
        )
        (tmp_path / "configs/quality/observability_slo_alert_contract.yaml").write_text(
            "{}\n",
            encoding="utf-8",
        )
        (tmp_path / "configs/quality/mandatory_tracing_coverage.yaml").write_text(
            "{}\n",
            encoding="utf-8",
        )
        (tmp_path / "grafana/prometheus-rules/bioetl_observability.yml").write_text(
            "groups: []\n",
            encoding="utf-8",
        )
        report = run_observability_contract_checks(tmp_path)
        assert report.passed is False
        inventory = next(
            check for check in report.checks if check.name == "metric_inventory_drift"
        )
        assert inventory.passed is False
        assert "error" in inventory.details


class TestLineageBlankIdentifiers:
    def test_blank_run_id_does_not_win_over_manifest(self) -> None:
        assert (
            _resolve_explain_identifier(run_id="   ", manifest_id="manifest-1")
            == "manifest-1"
        )

    def test_blank_both_returns_none(self) -> None:
        assert _resolve_explain_identifier(run_id="  ", manifest_id="") is None


class TestQuarantineServeHostDefault:
    def test_default_host_is_loopback(self) -> None:
        host_option = next(
            param for param in quarantine_serve.params if "--host" in param.opts
        )
        assert host_option.default == "127.0.0.1"
