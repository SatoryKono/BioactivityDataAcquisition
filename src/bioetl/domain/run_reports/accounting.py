"""In-run stage accounting accumulator for funnel + reason maps."""

from __future__ import annotations

from typing import override

from collections import defaultdict

from bioetl.domain.ports import StageAccountingPort
from bioetl.domain.run_reports._stage_bucket import _StageBucket
from bioetl.domain.run_reports.accounting_snapshots import (
    StageAccountingSnapshotsMixin,
)
from bioetl.domain.run_reports.models import (
    RemovalOutcome,
    StageId,
)
from bioetl.domain.run_reports.reason_catalog import (
    ReasonCatalog,
    default_reason_catalog,
    normalize_reason_code,
)

_MAX_SAMPLES = 20

# Stages considered instrumented by default high-volume hooks (R3).
_DEFAULT_INSTRUMENTED_STAGES = frozenset(
    {
        StageId.BRONZE.value,
        StageId.SILVER.value,
        StageId.GOLD.value,
    }
)


class StageAccountingAccumulator(StageAccountingSnapshotsMixin, StageAccountingPort):
    """Mutable per-run accumulator; snapshot methods are pure projections."""

    def __init__(
        self,
        *,
        catalog: ReasonCatalog | None = None,
        instrumented_stages: frozenset[str] | None = None,
    ) -> None:
        self._catalog = catalog or default_reason_catalog()
        self._stages: dict[str, _StageBucket] = defaultdict(_StageBucket)
        self._unmapped_reasons = 0
        self._instrumented_stages = instrumented_stages or _DEFAULT_INSTRUMENTED_STAGES
        self._touched_instrumented = False

    @property
    @override
    def reason_catalog_version(self) -> str:
        return self._catalog.version

    @property
    @override
    def unmapped_reason_count(self) -> int:
        return self._unmapped_reasons

    @override
    def mark_instrumented(self, stage: str) -> None:
        bucket = self._stages[stage]
        bucket.instrumented = True
        self._touched_instrumented = True

    @override
    def record_in(self, stage: str, count: int) -> None:
        if count <= 0:
            return
        self._stages[stage].records_in += int(count)

    @override
    def record_out(self, stage: str, count: int) -> None:
        if count <= 0:
            return
        self._stages[stage].records_out += int(count)

    @override
    def record_removal(
        self,
        stage: str,
        *,
        outcome: str,
        reason_code: str | None,
        count: int = 1,
        sample_ref: str | None = None,
    ) -> None:
        if count <= 0:
            return
        bucket = self._stages[stage]
        bucket.instrumented = True
        self._touched_instrumented = True
        code = normalize_reason_code(reason_code, self._catalog)
        if self._is_unmapped_reason(reason_code, code):
            self._unmapped_reasons += 1
        outcome_key = self._normalize_outcome(outcome, code)
        key = (outcome_key, code)
        bucket.removals[key] = bucket.removals.get(key, 0) + int(count)
        self._append_sample(bucket, key, sample_ref)

    def _is_unmapped_reason(self, reason_code: str | None, normalized: str) -> bool:
        if reason_code in (None, ""):
            return True
        return (
            normalized == self._catalog.unknown_code
            and reason_code != self._catalog.unknown_code
        )

    @staticmethod
    def _append_sample(
        bucket: _StageBucket,
        key: tuple[str, str],
        sample_ref: str | None,
    ) -> None:
        if sample_ref is None:
            return
        samples = bucket.samples.setdefault(key, [])
        if sample_ref not in samples and len(samples) < _MAX_SAMPLES:
            samples.append(sample_ref)

    def _normalize_outcome(self, outcome: str, reason_code: str) -> str:
        try:
            return RemovalOutcome(outcome).value
        except ValueError:
            return self._catalog.default_outcome_for(reason_code)

    def apply_layer_totals(
        self,
        *,
        bronze: int = 0,
        silver_valid: int = 0,
        gold_written: int = 0,
        records_fetched: int = 0,
    ) -> None:
        """Seed stage in/out from coarse run metrics when not already set."""
        self._seed_stage(
            StageId.EXTRACT.value,
            records_in=records_fetched,
            records_out=bronze or records_fetched,
        )
        self._seed_stage(
            StageId.BRONZE.value,
            records_in=bronze,
            records_out=bronze,
        )
        self._seed_stage(
            StageId.SILVER.value, records_in=bronze, records_out=silver_valid
        )
        self._seed_stage(
            StageId.GOLD.value, records_in=silver_valid, records_out=gold_written
        )

    def _seed_stage(self, stage: str, *, records_in: int, records_out: int) -> None:
        bucket = self._stages[stage]
        if records_in > 0 and bucket.records_in == 0:
            self.record_in(stage, records_in)
        if records_out > 0 and bucket.records_out == 0:
            self.record_out(stage, records_out)

    def sum_outcome(self, stage: str, outcome: str) -> int:
        """Return total removals for one stage/outcome."""
        bucket = self._stages.get(stage)
        if bucket is None:
            return 0
        return sum(
            count for (out, _code), count in bucket.removals.items() if out == outcome
        )

    @override
    def _sum_outcome(self, stage: str, outcome: str) -> int:
        return self.sum_outcome(stage, outcome)
