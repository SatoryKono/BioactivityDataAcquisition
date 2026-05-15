"""Focused tests for Silver replay-safe rerun contract helpers."""

from __future__ import annotations

import pyarrow as pa

from bioetl.infrastructure.storage.silver.delta_helpers import (
    build_replay_safe_rerun_contract,
)


def test_build_replay_safe_rerun_contract_is_machine_readable() -> None:
    """Silver merge rerun semantics should expose explicit external guards."""
    records = pa.table(
        {
            "id": [1],
            "content_hash": ["hash-1"],
            "_run_type": ["rebuild"],
        }
    )

    contract = build_replay_safe_rerun_contract(records)

    assert contract.merge_update_policy == "content_hash_only"
    assert contract.requires_content_hash is True
    assert contract.strict_replay_safe is True
    assert contract.external_guards == ("lifecycle_cleanup", "exclusive_locks")
