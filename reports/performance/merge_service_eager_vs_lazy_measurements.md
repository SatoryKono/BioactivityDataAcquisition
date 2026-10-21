# MergeService Eager vs Lazy Reading Measurements

## Objective
Measure the resource consumption (Peak RSS and Wall Time) and ensure semantic equivalence when reading Silver tables using eager reading (`pl.read_parquet`) vs lazy plan collection (`pl.scan_parquet().collect()`) to address the DOMAIN_STOP constraint.

## Methodology
- **Data Generation:** Simulated production-like ChEMBL Activity table data with corresponding columns, types, and sizes.
- **Sizes:** 1,000,000 rows (approx 3.9 MB disk space for parquet), 2,000,000 rows (approx 7.9 MB), and 5,000,000 rows (approx 20.1 MB).
- **Measurement Tooling:** `scripts/engineering/performance/measure_merge_eager.py` and `scripts/engineering/performance/run_measurements.sh`.
- Peak RSS was measured in an isolated run (without creating in-memory CSVs which polluted previous results). Hash checking was performed externally using `scripts/engineering/performance/check_hash.py`.
- Each size was measured once, eager then lazy. That order does not separate file-cache effects from the read API.

## Environment
```
=== ENVIRONMENT ===
Linux devbox 6.8.0 #1 SMP PREEMPT_DYNAMIC Fri Feb 20 20:38:43 UTC 2026 x86_64 x86_64 x86_64 GNU/Linux
Python: 3.13.14 (main, Jun 23 2026, 15:18:27) [Clang 22.1.3 ]
Polars: 2.0.0
01866ed7245d8e20ce3462ad8b3be83682ccf305
```

## Provenance
The raw logs are the immutable snapshot of that run. `/usr/bin/time` recorded the command that actually executed. Later hardening of `run_measurements.sh` to `uv run --frozen --no-build` does not rewrite those lines.

- `eager_1000000.txt`: Command being timed: "uv run python scripts/engineering/performance/measure_merge_eager.py eager 1000000"
- `eager_2000000.txt`: Command being timed: "uv run python scripts/engineering/performance/measure_merge_eager.py eager 2000000"
- `eager_5000000.txt`: Command being timed: "uv run python scripts/engineering/performance/measure_merge_eager.py eager 5000000"
- `lazy_1000000.txt`: Command being timed: "uv run python scripts/engineering/performance/measure_merge_eager.py lazy 1000000"
- `lazy_2000000.txt`: Command being timed: "uv run python scripts/engineering/performance/measure_merge_eager.py lazy 2000000"
- `lazy_5000000.txt`: Command being timed: "uv run python scripts/engineering/performance/measure_merge_eager.py lazy 5000000"

## Measurements Table

| Dataset Size | File Size on Disk | Strategy | Peak RSS (KB) | Wall Time (s) | Rows Read | SHA-256 Hash of Output (df.hash_rows()) |
| --- | --- | --- | --- | --- | --- | --- |
| 1,000,000 | 3,928,205 bytes | Eager | 491052 | 0.1584 | 1,000,000 | `bf86094c6684744fd77b7c276af998a99c7273dfd9ec31f72824945c93a1da88` |
| 1,000,000 | 3,928,205 bytes | Lazy | 490924 | 0.1556 | 1,000,000 | `bf86094c6684744fd77b7c276af998a99c7273dfd9ec31f72824945c93a1da88` |
| 2,000,000 | 7,978,772 bytes | Eager | 915244 | 0.2837 | 2,000,000 | `82f85d7bca77d9083e1d5c0adec90a6d09975f034ad4d5315957311ff66d3851` |
| 2,000,000 | 7,978,772 bytes | Lazy | 915632 | 0.2894 | 2,000,000 | `82f85d7bca77d9083e1d5c0adec90a6d09975f034ad4d5315957311ff66d3851` |
| 5,000,000 | 20,157,108 bytes | Eager | 2177640 | 0.7461 | 5,000,000 | `5e7b35d0af930ffcd5bcd2ab64564dc1de1c1ba2e85ca558889aa3b24b41cebb` |
| 5,000,000 | 20,157,108 bytes | Lazy | 2176380 | 0.7190 | 5,000,000 | `5e7b35d0af930ffcd5bcd2ab64564dc1de1c1ba2e85ca558889aa3b24b41cebb` |

## Semantic Equivalence
For all sizes (1M, 2M, 5M rows), the eager and lazy execution methods produced identical outputs:
- **Number of rows:** Matched the requested size in both `EAGER_ROWS` and `LAZY_ROWS`.
- **Data Content / Hashes:** `EAGER_HASH` and `LAZY_HASH` matched, and the hash log contains `HASHES_MATCH`.
- **Discrepancies:** None. Generation raises if a marker, row count, or hash check is missing or inconsistent.

## Verdict on DOMAIN_STOP
The `DOMAIN_STOP` rule forbids lazy-refactoring without a measured bottleneck.

Thresholds for a proven bottleneck: lazy wall time lower by at least 0.5 s and 10%, or lazy peak RSS lower by at least 10%.

Based on the measurements:
- Maximum lazy wall-time reduction: 0.0271 s (3.6%).
- Maximum lazy peak-RSS reduction: 0.1%.
- **Conclusion:** A bottleneck has **not been proven**. The eager execution mode remains the default until a reduction clears those thresholds.
