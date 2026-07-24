"""Snapshot/projection helpers for stage accounting accumulators."""

from __future__ import annotations

from bioetl.domain.run_reports._stage_bucket import _StageBucket
from bioetl.domain.run_reports.models import (
    BalanceStatus,
    LayerCounts,
    ReasonRemoval,
    StageFunnelRow,
    StageId,
    TrackingCoverage,
)


class StageAccountingSnapshotsMixin:
    """Projection methods shared by StageAccountingAccumulator."""

    def snapshot_layers_from_metrics(self, metrics: dict[str, int]) -> LayerCounts:
        """Build layer rollup from coarse metrics + removal maps."""
        silver_filtered = int(metrics.get("records_filtered_out", 0))
        silver_quarantined = int(metrics.get("records_quarantined", 0))
        gold_excluded = int(metrics.get("records_gold_excluded_by_contract", 0))

        mapped_filtered = self._sum_outcome(StageId.SILVER.value, "filtered_out")
        mapped_quarantined = self._sum_outcome(StageId.SILVER.value, "quarantined")
        mapped_dedup = self._sum_outcome(StageId.SILVER.value, "deduplicated")
        mapped_skipped = self._sum_outcome(StageId.SILVER.value, "skipped")
        mapped_gold_excluded = self._sum_outcome(
            StageId.GOLD.value, "excluded_by_contract"
        )
        mapped_gold_quarantined = self._sum_outcome(StageId.GOLD.value, "quarantined")
        mapped_gold_dedup = self._sum_outcome(StageId.GOLD.value, "deduplicated")
        mapped_gold_skipped = self._sum_outcome(StageId.GOLD.value, "skipped")

        return LayerCounts(
            bronze_records=int(metrics.get("records_bronze", 0)),
            silver_valid=int(metrics.get("records_silver", 0)),
            silver_filtered_out=mapped_filtered or silver_filtered,
            silver_quarantined=mapped_quarantined or silver_quarantined,
            silver_skipped=mapped_skipped,
            silver_deduplicated=mapped_dedup,
            gold_written=int(metrics.get("records_gold", 0)),
            gold_excluded_by_contract=mapped_gold_excluded or gold_excluded,
            gold_quarantined=mapped_gold_quarantined,
            gold_skipped=mapped_gold_skipped,
            gold_deduplicated=mapped_gold_dedup,
        )

    def snapshot_funnel(self, layers: LayerCounts) -> tuple[StageFunnelRow, ...]:
        """Project ordered funnel rows with conservation checks."""
        order = (
            StageId.EXTRACT.value,
            StageId.BRONZE.value,
            StageId.SILVER.value,
            StageId.GOLD.value,
        )
        return tuple(
            self._build_funnel_row(
                stage_id,
                self._stages.get(stage_id, _StageBucket()),
                layers,
            )
            for stage_id in order
        )

    def _build_funnel_row(
        self,
        stage_id: str,
        bucket: _StageBucket,
        layers: LayerCounts,
    ) -> StageFunnelRow:
        removals = self._removals_for_bucket(bucket)
        removed_mapped = sum(item.count for item in removals)
        default_in, default_out, default_removed = self._stage_defaults(stage_id, layers)
        records_in = bucket.records_in or default_in
        records_out = bucket.records_out or default_out
        removed_total = removed_mapped or default_removed
        records_in, records_out, removed_total = self._prefer_conserving_projection(
            records_in=records_in,
            records_out=records_out,
            removed_total=removed_total,
            default_in=default_in,
            default_out=default_out,
            default_removed=default_removed,
            removed_mapped=removed_mapped,
        )
        unaccounted = max(0, records_in - records_out - removed_total)
        tracking = self._tracking_for(stage_id, bucket)
        return StageFunnelRow(
            stage_id=stage_id,
            records_in=records_in,
            records_out=records_out,
            removed_total=removed_total,
            removals=removals,
            balance_status=self._balance_status(
                records_in=records_in,
                records_out=records_out,
                removed_total=removed_total,
                unaccounted=unaccounted,
                tracking=tracking,
            ),
            tracking=tracking,
            unaccounted=unaccounted,
        )

    @staticmethod
    def _prefer_conserving_projection(
        *,
        records_in: int,
        records_out: int,
        removed_total: int,
        default_in: int,
        default_out: int,
        default_removed: int,
        removed_mapped: int,
    ) -> tuple[int, int, int]:
        """Prefer layer-aligned in/out when bucket values break conservation.

        High-volume hooks may over-count ``records_out`` (e.g. gold batch
        metrics). Layer totals from RunResult remain the coarse SoT for
        funnel geometry; removal reason maps still come from the bucket.
        """
        if records_in == records_out + removed_total:
            return records_in, records_out, removed_total
        layer_removed = removed_mapped if removed_mapped > 0 else default_removed
        if default_in > 0 and default_in == default_out + layer_removed:
            return default_in, default_out, layer_removed
        return records_in, records_out, removed_total

    @staticmethod
    def _stage_defaults(
        stage_id: str,
        layers: LayerCounts,
    ) -> tuple[int, int, int]:
        silver_removed = (
            layers.silver_filtered_out
            + layers.silver_quarantined
            + layers.silver_skipped
            + layers.silver_deduplicated
        )
        gold_removed = (
            layers.gold_excluded_by_contract
            + layers.gold_quarantined
            + layers.gold_skipped
            + layers.gold_deduplicated
        )
        return {
            StageId.EXTRACT.value: (
                layers.bronze_records,
                layers.bronze_records,
                0,
            ),
            StageId.BRONZE.value: (
                layers.bronze_records,
                layers.bronze_records,
                0,
            ),
            StageId.SILVER.value: (
                layers.bronze_records,
                layers.silver_valid,
                silver_removed,
            ),
            StageId.GOLD.value: (
                layers.silver_valid,
                layers.gold_written,
                gold_removed,
            ),
        }[stage_id]

    def _removals_for_bucket(self, bucket: _StageBucket) -> tuple[ReasonRemoval, ...]:
        items: list[ReasonRemoval] = []
        for (outcome, code), count in sorted(
            bucket.removals.items(), key=lambda item: (-item[1], item[0][0], item[0][1])
        ):
            entry = self._catalog.resolve(code)
            samples = tuple(bucket.samples.get((outcome, code), ()))
            items.append(
                ReasonRemoval(
                    outcome=outcome,
                    reason_code=code,
                    count=count,
                    reason_family=entry.family,
                    sample_refs=samples,
                )
            )
        return tuple(items)

    def _tracking_for(self, stage_id: str, bucket: _StageBucket) -> TrackingCoverage:
        if self._is_configured(stage_id, bucket) and self._is_touched(bucket):
            return self._configured_tracking(bucket)
        if self._is_configured(stage_id, bucket):
            return TrackingCoverage.PARTIAL
        if stage_id == StageId.EXTRACT.value:
            return TrackingCoverage.PARTIAL
        return TrackingCoverage.NOT_TRACKED

    def _is_configured(self, stage_id: str, bucket: _StageBucket) -> bool:
        return bucket.instrumented or stage_id in self._instrumented_stages

    def _is_touched(self, bucket: _StageBucket) -> bool:
        return self._touched_instrumented or bool(bucket.removals)

    @staticmethod
    def _configured_tracking(bucket: _StageBucket) -> TrackingCoverage:
        return (
            TrackingCoverage.FULL
            if bucket.instrumented
            else TrackingCoverage.PARTIAL
        )

    @staticmethod
    def _balance_status(
        *,
        records_in: int,
        records_out: int,
        removed_total: int,
        unaccounted: int,
        tracking: TrackingCoverage,
    ) -> BalanceStatus:
        if records_in == records_out + removed_total:
            return BalanceStatus.OK
        if _is_unknown_balance(records_in, tracking):
            return BalanceStatus.UNKNOWN
        if _is_degraded_balance(unaccounted, tracking):
            return BalanceStatus.DEGRADED
        return BalanceStatus.FAILING

    def overall_tracking_coverage(
        self, funnel: tuple[StageFunnelRow, ...]
    ) -> TrackingCoverage:
        statuses = {row.tracking for row in funnel}
        if statuses == {TrackingCoverage.FULL}:
            return TrackingCoverage.FULL
        if statuses & {TrackingCoverage.FULL, TrackingCoverage.PARTIAL}:
            return TrackingCoverage.PARTIAL
        return TrackingCoverage.NOT_TRACKED

    def top_reasons(self, limit: int = 10) -> tuple[dict[str, object], ...]:
        totals: dict[tuple[str, str, str | None], int] = {}
        for stage_bucket in self._stages.values():
            for (outcome, code), count in stage_bucket.removals.items():
                family = self._catalog.family_for(code)
                key = (code, outcome, family)
                totals[key] = totals.get(key, 0) + count
        ranked = sorted(totals.items(), key=lambda item: (-item[1], item[0][0]))
        result: list[dict[str, object]] = []
        for (code, outcome, family), count in ranked[:limit]:
            result.append(
                {
                    "reason_code": code,
                    "outcome": outcome,
                    "reason_family": family,
                    "count": count,
                }
            )
        return tuple(result)


def _is_unknown_balance(records_in: int, tracking: TrackingCoverage) -> bool:
    return records_in == 0 and tracking is TrackingCoverage.NOT_TRACKED


def _is_degraded_balance(unaccounted: int, tracking: TrackingCoverage) -> bool:
    return unaccounted > 0 and tracking is TrackingCoverage.PARTIAL
