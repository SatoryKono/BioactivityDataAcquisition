"""Opt-in pytest inputs for byte-level CI replay comparison.

Load only with ``-p scripts.engineering.ci.replay_parity_inputs``. Operational
clocks and occurrence seeds are inputs, not replay output normalization. Each
run still produces distinct within-run occurrence IDs and checkpoint entries.
The scheduler clock and timeout clocks remain real; only persisted storage
metadata duration counters are fixed. No output field is removed or rewritten.
"""

from __future__ import annotations

from datetime import UTC, datetime
from itertools import count
from types import SimpleNamespace

import pytest


@pytest.fixture(autouse=True)
def stable_replay_inputs(
    monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
):
    """Supply identical operational inputs to independent determinism runs."""
    if "tests/integration/determinism/" not in request.node.path.as_posix():
        return

    from bioetl.composition import occurrence_identity
    from bioetl.infrastructure.checkpoint import _local_checkpoint_io
    from bioetl.infrastructure.storage import bronze_writer
    from bioetl.infrastructure.storage.silver import (
        metadata_mixin,
        writer_runtime_support,
    )
    from bioetl.infrastructure.time import SystemClock

    monkeypatch.setattr(
        occurrence_identity, "_PROCESS_OCCURRENCE_SEED", {"case": request.node.nodeid}
    )
    monkeypatch.setattr(occurrence_identity, "_SCOPE_COUNTERS", {})
    monkeypatch.setattr(
        SystemClock, "now", lambda _self: datetime(2026, 1, 1, tzinfo=UTC)
    )
    checkpoint_clock = count(1767225600000000000)
    monkeypatch.setattr(
        _local_checkpoint_io,
        "time",
        SimpleNamespace(time_ns=lambda: next(checkpoint_clock)),
    )
    for module in (bronze_writer, metadata_mixin, writer_runtime_support):
        monkeypatch.setattr(
            module, "time", SimpleNamespace(perf_counter=lambda: 1000.0)
        )
