"""Shared PreSilver identity host protocol for staging/finalization flows."""

from __future__ import annotations

from typing import Protocol

from bioetl.domain.types import EntityID, GoldRecord


class PreSilverIdentityHost(Protocol):
    """Host surface that can resolve entity IDs for PreSilver staging."""
    def compute_entity_id(
        self,
        source_id: str | None,
        record: GoldRecord,
    ) -> EntityID: ...
