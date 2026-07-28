______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-07-28'

______________________________________________________________________

# Performance Tuning Guide

**Issue:** #6548
**Related:** [performance-baselines.md](performance-baselines.md), ADR-010, ADR-032, ADR-014

## Principles

1. Measure with a **fixed fixture / replayable input** before changing knobs.
2. Prefer batch-size and backpressure fixes over “more threads” on Local-Only.
3. Deterministic writes (ADR-014) constrain reorder tricks — do not break sort contracts.
4. HTTP cost often dominates: tune ADR-032 client before micro-optimizing pandas.

## Pipeline knobs

| Area | Levers | Notes |
| --- | --- | --- |
| Batch size | entity/provider config batch settings | Memory vs round-trips |
| Extract concurrency | provider client limits | Respect rate limits |
| Transform | vectorized mapping, avoid per-row Python where hot | Profile first |
| Silver merge | sort_by, partition-by, batch commit size | Delta ACID cost |
| Checkpoint | frequency vs recovery cost | Lifecycle runbooks |

## HTTP client (ADR-032)

- Connection reuse / pooling via unified client
- Rate limit + retry + circuit breaker thresholds
- Timeouts: connect vs read
- Avoid retry storms on permanent 4xx

## Data / I/O

- Bronze: sequential append; avoid needless rewrite
- Silver: minimize full table rewrites; keep merge keys stable
- Gold: strict validation cost scales with row count — sample during debug
- Local disk: keep `data/` on fast volume; exclude from antivirus hot paths if needed

## Profiling

```bash
# example shapes — use project test runners when available
python -m cProfile -o /tmp/bioetl.prof -m bioetl ...
```

Memory: track batch peaks; lower batch size before adding swap.

## Testing performance

- Prefer narrow pytest selection over full suite while iterating
- VCR cassettes reduce live HTTP variance
- See [test-optimization-guide.md](../03-guides/test-optimization-guide.md)

## Related runbooks

- [pipeline-failure-recovery](runbooks/pipeline-failure-recovery.md)
- [metrics-monitoring](../03-guides/metrics-monitoring.md)
