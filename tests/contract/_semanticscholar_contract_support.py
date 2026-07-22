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
