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
"""Focused tests for Silver replay-safe rerun contract helpers."""

from __future__ import annotations

import pytest

import pyarrow as pa

from bioetl.infrastructure.storage.silver.delta_helpers import (
    build_replay_safe_rerun_contract,
)


pytestmark = pytest.mark.unit


def test_build_replay_safe_rerun_contract_is_machine_readable() -> None:
    """Silver merge rerun semantics should expose explicit external guards."""
    records = pa.table(
        {
            "id": [1],
            "content_hash": ["hash-1"],
            "_run_type": ["rebuild"],
        }
    )

    contract = build_replay_safe_rerun_contract(records)

    assert contract.merge_update_policy == "content_hash_only"
    assert contract.requires_content_hash is True
    assert contract.strict_replay_safe is True
    assert contract.external_guards == ("lifecycle_cleanup", "exclusive_locks")
