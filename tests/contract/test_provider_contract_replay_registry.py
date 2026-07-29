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
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Registry checks for provider contract replay coverage."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from tests.contract._provider_contract_replay import PROVIDER_CONTRACT_REPLAY_PROBES

ROOT = Path(__file__).resolve().parents[2]
TEST_MATRIX_PATH = ROOT / "configs" / "quality" / "test_matrix.yaml"
DRIFT_WORKFLOW_PATH = ROOT / ".github" / "workflows" / "provider-contract-drift.yml"
LIVE_WORKFLOW_PATH = ROOT / ".github" / "workflows" / "contract-tests.yml"

pytestmark = [pytest.mark.no_api, pytest.mark.contracts]


def test_replay_registry_covers_all_required_snapshot_probes() -> None:
    payload = cast(
        dict[str, Any], yaml.safe_load(TEST_MATRIX_PATH.read_text(encoding="utf-8"))
    )
    registry = cast(
        dict[str, Any], payload["fixture_governance"]["contract_snapshot_registry"]
    )
    expected = {
        (provider, probe)
        for provider, provider_payload in cast(
            dict[str, dict[str, Any]], registry["providers"]
        ).items()
        for probe in cast(list[str], provider_payload["required_probes"])
    }
    actual = {(case.provider, case.probe) for case in PROVIDER_CONTRACT_REPLAY_PROBES}

    assert actual == expected


def test_replay_registry_points_to_existing_cassettes() -> None:
    for case in PROVIDER_CONTRACT_REPLAY_PROBES:
        assert case.cassette_path.exists(), case.cassette_rel_path


def test_replay_registry_and_workflows_keep_offline_and_live_modes_separate() -> None:
    drift_workflow = cast(
        dict[str, Any], yaml.safe_load(DRIFT_WORKFLOW_PATH.read_text(encoding="utf-8"))
    )
    live_workflow = cast(
        dict[str, Any], yaml.safe_load(LIVE_WORKFLOW_PATH.read_text(encoding="utf-8"))
    )

    drift_env = cast(dict[str, str], drift_workflow.get("env", {}))
    live_env = cast(dict[str, str], live_workflow.get("env", {}))

    assert drift_env.get("VCR_RECORD_MODE") == "none"
    assert "BIOETL_LIVE_API_TESTS" not in drift_env
    assert "BIOETL_NETWORK_TESTS" not in drift_env
    assert live_env.get("BIOETL_LIVE_API_TESTS") == "true"
    assert live_env.get("BIOETL_NETWORK_TESTS") == "true"
