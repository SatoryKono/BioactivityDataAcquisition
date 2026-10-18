# Eager Merger Input Measurement Report (Issue 12045 Phase 0)

Generated at: 2026-10-18T15:09:21.336988Z

## Measurement Environment
- Operation: `_read_silver_table` (Delta -> Arrow -> Polars)
- Dataset: Synthetic Deterministic Activity/Target schema
- Execution: Isolated processes per scale

## Results

| Scale (Rows) | Status | Wall Time (s) | Peak RSS (MB) |
| --- | --- | --- | --- |
| 10,000 | COMPLETED | 0.137 | 233.0 |
| 100,000 | COMPLETED | 0.154 | 317.3 |
| 500,000 | COMPLETED | 0.303 | 545.9 |
| 1,000,000 | COMPLETED | 0.584 | 746.7 |
| 2,500,000 | COMPLETED | 1.020 | 1677.4 |
| 5,000,000 | COMPLETED | 1.350 | 2562.8 |

## Conclusion

**Bottleneck Confirmed**: Performance degrades significantly at higher scales, confirming the gap.
