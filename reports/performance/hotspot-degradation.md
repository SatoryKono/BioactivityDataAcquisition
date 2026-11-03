# Hotspot Degradation Report

- window_size: 5
- benchmarks_total: 5
- within_budget: 5
- over_budget: 0

| Benchmark | Samples | Lat(ms) | P95(ms) | Thr(r/s) | Lat Reg | P95 Reg | Thr Reg | Budget | Status | Trend |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| atomic_write_group_50 | 1 | 0.99 | 1.11 | 50527.61 | -4.1% | -97.8% | -4.3% | 30.0% | PASS | `----------------` |
| crossref_batch_fetch_200 | 1 | 0.24 | 0.33 | 837103.79 | -2.9% | 52.5% | -3.0% | 150.0% | PASS | `########--------` |
| silver_prepare_arrow_2000 | 1 | 2.11 | 2.25 | 949804.72 | 3.3% | -78.4% | 3.2% | 25.0% | PASS | `----------------` |
| silver_write_append_600 | 1 | 23.72 | 24.67 | 25293.19 | 8.5% | -41.3% | 7.8% | 60.0% | PASS | `#---------------` |
| silver_write_merge_600 | 1 | 49.21 | 51.03 | 12192.21 | 1.6% | -28.2% | 1.6% | 70.0% | PASS | `----------------` |
