"""Stream B APP: leftover default historical-closure verdict."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bioetl.application.services.control_plane.replay.historical_closure_policy import (
    resolve_closure_verdict,
)

pytestmark = pytest.mark.unit


def test_closure_verdict_residual_program_in_progress() -> None:
    inventory = SimpleNamespace(
        manifest_count=2,
        certified_count=1,
        replayable_count=0,
        unsupported_count=0,
        remaining_uncertified_count=1,
    )
    verdict, reason = resolve_closure_verdict(
        inventory=inventory,  # type: ignore[arg-type]
        unresolved_records=(),
        disposition_map={},
        claim_scope_mode="all_retained_historical_runs",
    )
    assert verdict == "residual_resolution_program_in_progress"
    assert "not_yet_closed" in reason
