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
"""Replay-backed Semantic Scholar contract support.

Historically this module contained live-network probing helpers. Contract tests
now consume replay payload fixtures via ``tests.contract.conftest``; this module
retains a narrow compatibility surface for any legacy imports.
"""

from __future__ import annotations

from tests.contract.conftest import _load_semanticscholar_replay_payload


def load_semanticscholar_replay_payload(*, probe: str) -> object:
    """Load a replay payload for one Semantic Scholar contract probe.

    ``probe`` must be one of:
    - ``paper_search_endpoint``
    - ``paper_batch_lookup_by_doi``
    """
    return _load_semanticscholar_replay_payload(probe)
