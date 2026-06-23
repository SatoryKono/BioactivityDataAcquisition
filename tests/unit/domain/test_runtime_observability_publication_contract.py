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
