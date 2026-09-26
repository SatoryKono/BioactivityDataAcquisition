"""Port for run-scoped stage accounting."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from bioetl.domain.run_reports.models import LayerCounts, StageFunnelRow


@runtime_checkable
class StageAccountingPort(Protocol):
    """Record and project bounded per-run funnel accounting."""

    @property
    def reason_catalog_version(self) -> str:
        """Return the stable reason-catalog version."""
        ...

    @property
    def unmapped_reason_count(self) -> int:
        """Return the number of removals mapped to the unknown reason."""
        ...

    def mark_instrumented(self, stage: str) -> None:
        """Declare that a stage has an active accounting hook."""
        ...

    def record_in(self, stage: str, count: int) -> None:
        """Record records entering a stage."""
        ...

    def record_out(self, stage: str, count: int) -> None:
        """Record records retained by a stage."""
        ...

    def record_removal(
        self,
        stage: str,
        *,
        outcome: str,
        reason_code: str | None,
        count: int = 1,
        sample_ref: str | None = None,
    ) -> None:
        """Record a stable, reason-coded removal aggregate."""
        ...

    def snapshot_layers_from_metrics(self, metrics: dict[str, int]) -> LayerCounts:
        """Build the Processed Records-compatible layer projection."""
        ...

    def snapshot_funnel(self, layers: LayerCounts) -> tuple[StageFunnelRow, ...]:
        """Build the deterministic stage funnel projection."""
        ...
