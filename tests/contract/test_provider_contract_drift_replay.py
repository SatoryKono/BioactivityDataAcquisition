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
"""Offline replay checks for provider contract drift."""

from __future__ import annotations

from typing import Any, cast

import pytest

from tests.contract._provider_contract_replay import (
    PROVIDER_CONTRACT_REPLAY_PROBES,
    ProviderContractReplayProbe,
    build_provider_contract_replay_report,
)

pytestmark = [pytest.mark.no_api, pytest.mark.contracts]


@pytest.mark.parametrize(
    "case",
    PROVIDER_CONTRACT_REPLAY_PROBES,
    ids=lambda case: f"{case.provider}:{case.probe}",
)
def test_provider_contract_replay_cases_do_not_break(
    case: ProviderContractReplayProbe,
) -> None:
    report = build_provider_contract_replay_report(case)

    assert report["severity"] != "breaking", _render_report(report)


def _render_report(report: dict[str, Any]) -> str:
    lines = [
        f"{report['provider']}.{report['probe']}: replay contract drift",
        f"entity={report['entity']}",
        f"severity={report['severity']}",
        f"status={report['status']}",
        f"cassette={report['cassette_rel_path']}",
        f"interaction_index={report['interaction_index']}",
    ]
    for difference in cast(list[dict[str, Any]], report["differences"]):
        lines.append(
            "  "
            f"{difference['path']}: expected {difference['expected_type']!r}, "
            f"got {difference['actual_type']!r} "
            f"({difference['severity']}; {difference['detail']}; "
            f"remediation={difference['remediation']})"
        )
    return "\n".join(lines)
