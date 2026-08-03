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
"""Repository-backed test for the Codex/Devin skill mirror contract."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.ai import sync_ai_governance


pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]
ROOT = Path(__file__).resolve().parents[4]


@pytest.mark.timeout(180)
def test_repository_skill_parity_contract_passes() -> None:
    """Exercise canonical runtime parity without a nested Python subprocess."""
    contract = sync_ai_governance._load_skills_mirror_contract(ROOT)
    paths = sync_ai_governance._contract_paths(ROOT, contract)
    issues = sync_ai_governance._validate_codex_devin_parity(paths, contract)

    assert issues == []
