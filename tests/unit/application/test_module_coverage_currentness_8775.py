"""Regression vectors for SHA-bound module coverage currentness (#8775)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.application.core.batch_executor_state_flow import process_stateful_batch
from bioetl.application.services.control_plane.manifest.diagnostics.replay_refresh_support import (
    _refresh_replay_summary_from_materialized_snapshots,
)
from bioetl.application.services.control_plane.replay import historical_corpus_service
from bioetl.application.services.control_plane.replay.reproducibility_score_cards_aggregation import (
    evaluate_threshold_failures,
)
from bioetl.application.services.control_plane.replay.reproducibility_score_cards_category_scores_core import (
    score_checkpoint_safety,
)
from bioetl.application.services.control_plane.replay.reproducibility_score_cards_category_scores_extended import (
    score_replay_readiness,
)


pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_batch_state_flow_skips_disallowed_process_command() -> None:
    assembled_state = object()
    host = SimpleNamespace(
        _fsm=MagicMock(
            advance=MagicMock(
                return_value=SimpleNamespace(
                    new_state=assembled_state, commands=frozenset()
                )
            )
        ),
        _fsm_state=object(),
    )

    await process_stateful_batch(host, [], 0)

    host._fsm.advance.assert_called_once()
    assert host._fsm_state is assembled_state


def test_replay_refresh_returns_summary_without_snapshot_payloads() -> None:
    summary: dict[str, object] = {"input_snapshots": ["not-a-snapshot"]}

    assert (
        _refresh_replay_summary_from_materialized_snapshots(
            manifest=object(),  # type: ignore[arg-type]
            summary=summary,
        )
        is summary
    )


def test_historical_diagnostics_rejects_non_mapping_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    diagnostics = SimpleNamespace(build_diagnostics_summary=lambda *_a, **_k: [])
    monkeypatch.setattr(
        historical_corpus_service,
        "import_module",
        lambda _name: diagnostics,
    )

    with pytest.raises(TypeError, match="expected mapping"):
        historical_corpus_service._build_diagnostics_summary(object())


def test_score_card_residual_failure_branches_are_explicit() -> None:
    failures = evaluate_threshold_failures(
        thresholds={"identity": 8},
        category_scores={},
    )
    checkpoint = score_checkpoint_safety(
        {
            "required_persistence_profile": "replay_ready",
            "resume_contract": {
                "applied_checkpoint_compatibility_policy": "warn",
                "resume_requested": False,
            },
        }
    )
    replay = score_replay_readiness(
        {
            "exact_replay_eligible": True,
            "replay_mode": "rebuild_only",
            "artifact_publication_closure": "closed",
        }
    )

    assert failures[0]["reason"] == "category_score_missing"
    assert "checkpoint_policy_below_profile_minimum" in checkpoint.blockers
    assert "rebuild_only_replay_mode" in replay.blockers
