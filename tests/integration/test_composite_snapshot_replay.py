"""Opt-in offline replay proof for each live composite acceptance case."""

import os
from pathlib import Path

import pytest

from scripts.ops.observability.composite_replay_acceptance import execute_replay
from scripts.ops.observability.green_acceptance import discover, launch_timeout

ROOT = Path(__file__).resolve().parents[2]
CASES = [case for case in discover(ROOT) if case.kind == "composite"]


@pytest.mark.skipif(
    os.environ.get("BIOETL_REPLAY_ACCEPTANCE") != "1",
    reason="Explicit saved composite replay opt-in required",
)
@pytest.mark.parametrize(
    "case",
    [
        pytest.param(
            case,
            id=case.id,
            marks=pytest.mark.timeout(launch_timeout(case, ROOT) + 120),
        )
        for case in CASES
    ],
)
def test_composite_replays_without_external_network(case):
    failures = execute_replay(
        case,
        ROOT,
        Path(os.environ["BIOETL_REPLAY_SOURCE_ROOT"]).resolve() / case.id,
        Path(os.environ["BIOETL_REPLAY_OUTPUT"]).resolve(),
        Path(os.environ["BIOETL_GREEN_ENV_FILE"]).resolve(),
    )
    assert not failures, "\n".join(failures)
