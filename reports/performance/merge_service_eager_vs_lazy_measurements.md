# MergeService Eager vs Lazy Reading Measurements

## Objective
Measure the resource consumption (Peak RSS and Wall Time) and ensure semantic equivalence when reading Silver tables using eager reading (`pl.read_parquet`) vs lazy plan collection (`pl.scan_parquet().collect()`) to address the DOMAIN_STOP constraint.

## Methodology
- **Data Generation:** Simulated production-like ChEMBL Activity table data with corresponding columns, types, and sizes.
- **Sizes:** 1,000,000 rows (approx 3.9 MB disk space for parquet), 2,000,000 rows (approx 7.9 MB), and 5,000,000 rows (approx 20.1 MB).
- **Measurement Tooling:** `scripts/engineering/performance/measure_merge_eager.py` and `scripts/engineering/performance/run_measurements.sh`.
- Peak RSS was measured in an isolated run (without creating in-memory CSVs which polluted previous results). Hash checking was performed externally using `check_hash.py`.

## Environment
```
=== ENVIRONMENT ===
Linux devbox 6.8.0 #1 SMP PREEMPT_DYNAMIC Fri Feb 20 20:38:43 UTC 2026 x86_64 x86_64 x86_64 GNU/Linux
Python: 3.13.14 (main, Jun 23 2026, 15:18:27) [Clang 22.1.3 ]
Polars: 2.0.0
01866ed7245d8e20ce3462ad8b3be83682ccf305
```

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
- **Number of rows:** Matched exactly.
- **Data Content / Hashes:** Output of `df.hash_rows().to_numpy().tobytes()` hashed with SHA-256 matched exactly for both APIs.
- **Discrepancies:** None.

## Verdict on DOMAIN_STOP
The `DOMAIN_STOP` rule forbids lazy-refactoring without a measured bottleneck.

Based on the measurements:
- The maximum performance gain (wall time) when using lazy evaluation across 5 million rows is marginal (e.g., ~0.02 seconds or ~3.5% improvement).
- The memory usage (Peak RSS) is virtually identical for both eager and lazy strategies across all scales, and the differences are within the noise margin.
- **Conclusion:** A bottleneck has **not been proven**. The eager execution mode behaves efficiently. There is no significant runtime or memory advantage to warrant a refactoring to the lazy API.
