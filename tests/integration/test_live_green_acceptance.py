"""Opt-in live launch matrix; selected cases never skip missing/failed evidence."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from scripts.ops.observability.green_acceptance import discover, execute

ROOT = Path(__file__).resolve().parents[2]
CASES = discover(ROOT)


@pytest.mark.network
@pytest.mark.timeout(1900)
@pytest.mark.skipif(
    os.environ.get("BIOETL_GREEN_ACCEPTANCE") != "1",
    reason="Explicit live launch opt-in required",
)
@pytest.mark.parametrize("case", CASES, ids=lambda case: case.id)
def test_live_run_is_green(case):
    output = Path(os.environ["BIOETL_GREEN_OUTPUT"]).resolve()
    env_file = Path(os.environ["BIOETL_GREEN_ENV_FILE"]).resolve()
    failures = execute(case, ROOT, output, env_file)
    assert not failures, "\n".join(failures)
