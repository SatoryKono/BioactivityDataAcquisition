"""Architecture guardrails for deterministic domain aggregate identities."""

from __future__ import annotations

import pytest

from pathlib import Path


pytestmark = pytest.mark.architecture

DOMAIN_IDENTITY_SURFACES = (
    Path("src/bioetl/domain/aggregates/events.py"),
    Path("src/bioetl/domain/aggregates/_batch_aggregate.py"),
    Path("src/bioetl/domain/aggregates/_quarantine_aggregate.py"),
)


def test_domain_aggregate_identity_surfaces_do_not_call_uuid4() -> None:
    """Replay-sensitive domain aggregate identities must be content-derived."""
    offenders = [
        str(path)
        for path in DOMAIN_IDENTITY_SURFACES
        if "uuid4" in path.read_text(encoding="utf-8")
    ]

    assert offenders == []
