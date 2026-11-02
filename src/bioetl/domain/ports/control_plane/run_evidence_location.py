"""Narrow read/register ports for run evidence location locators.

These ports are intentionally separate from ``RunManifestPort`` /
``RunLedgerPort``. They must not expand those ports' duties and must not
introduce backend writes into read-only Ops / Run Explorer paths.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from bioetl.domain.control_plane.run_evidence_location import (
    EvidenceLocationKind,
    EvidenceLocationLookupResult,
    EvidenceLocationRegisterResult,
    RunEvidenceLocation,
)

__all__ = [
    "RunEvidenceLocationReadPort",
    "RunEvidenceLocationRegisterPort",
]


@runtime_checkable
class RunEvidenceLocationReadPort(Protocol):
    """Read one evidence-location locator by ownership key."""

    def get(
        self,
        *,
        kind: EvidenceLocationKind | str,
        owner: str,
        run_id: str,
    ) -> RunEvidenceLocation | None:
        """Return the locator for one ownership key, or ``None`` when missing.

        Args:
            kind: Catalog kind (``pipeline`` or ``workflow``).
            owner: Owning pipeline or workflow identifier segment.
            run_id: Run identifier segment for the locator record.
        """
        ...

    def lookup(
        self,
        *,
        kind: EvidenceLocationKind | str,
        owner: str,
        run_id: str,
        expected_runtime_source_id: str | None = None,
    ) -> EvidenceLocationLookupResult:
        """Classify found / missing / invalid / identity conflict without a verdict.

        Args:
            kind: Catalog kind (``pipeline`` or ``workflow``).
            owner: Owning pipeline or workflow identifier segment.
            run_id: Run identifier segment for the locator record.
            expected_runtime_source_id: Optional runtime/bind source digest to
                compare against the stored locator; ``None`` skips identity check.
        """
        ...


@runtime_checkable
class RunEvidenceLocationRegisterPort(Protocol):
    """Register a locator with idempotent-identical / explicit-conflict semantics."""

    def register(self, location: RunEvidenceLocation) -> EvidenceLocationRegisterResult:
        """Persist ``location`` when absent; no-op when identical; conflict otherwise.

        Implementations MUST NOT fall back to another run's locator on conflict
        or invalid existing bytes. Conflict raises or returns
        ``EvidenceLocationRegisterOutcome.CONFLICT`` consistently with the
        domain ``decide_register_outcome`` contract; adapters that raise must
        use ``EvidenceLocationConflictError``.

        Args:
            location: Validated evidence-location locator to register.
        """
        ...
