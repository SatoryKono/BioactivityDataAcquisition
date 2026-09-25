"""Cover request-local evidence stage timing."""

from __future__ import annotations

import pytest

from bioetl.application.observability.control_plane_evidence.timing import (
    evidence_stage,
    observe_evidence_stages,
)

pytestmark = pytest.mark.unit


def test_evidence_stage_records_success_and_failure_only_with_observer() -> None:
    seen: list[tuple[str, float]] = []

    with evidence_stage("idle"):
        pass
    assert seen == []

    def _record(name: str, elapsed: float) -> None:
        seen.append((name, elapsed))

    with observe_evidence_stages(_record):
        with evidence_stage("load"):
            pass
        with pytest.raises(RuntimeError, match="boom"):
            with evidence_stage("fail"):
                raise RuntimeError("boom")

    assert [name for name, _elapsed in seen] == ["load", "fail"]
    assert all(elapsed >= 0 for _name, elapsed in seen)
