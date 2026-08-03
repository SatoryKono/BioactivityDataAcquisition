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
"""Unit tests for the runtime observability publication contract."""

from __future__ import annotations

import pytest

from bioetl.domain.runtime_observability_publication_contract import (
    CANONICAL_DOMAIN_EVENT_EMITTER,
    CANONICAL_LIFECYCLE_EMITTER,
    get_runtime_observability_publication_contract,
    is_canonical_runtime_observability_emitter,
)


pytestmark = pytest.mark.unit


def test_contract_freezes_canonical_emitters() -> None:
    contract = get_runtime_observability_publication_contract()

    assert contract.canonical_emitters == (
        CANONICAL_LIFECYCLE_EMITTER,
        CANONICAL_DOMAIN_EVENT_EMITTER,
    )
    assert contract.lifecycle_route.event_vocabulary == (
        "bioetl.domain.events.PipelineEvent"
    )
    assert (
        contract.domain_event_route.mapping_module
        == "bioetl.domain.observability_event_mapping"
    )


def test_contract_marks_only_pipeline_observer_emitters_as_canonical() -> None:
    assert is_canonical_runtime_observability_emitter("PipelineObserver.emit_event")
    assert is_canonical_runtime_observability_emitter(
        "PipelineObserver.emit_domain_event"
    )
    assert not is_canonical_runtime_observability_emitter("logger.info")
