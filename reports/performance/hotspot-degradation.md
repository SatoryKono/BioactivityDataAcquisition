# Hotspot Degradation Report

- window_size: 5
- benchmarks_total: 5
- within_budget: 5
- over_budget: 0

| Benchmark | Samples | Lat(ms) | P95(ms) | Thr(r/s) | Lat Reg | P95 Reg | Thr Reg | Budget | Status | Trend |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| atomic_write_group_50 | 1 | 0.99 | 1.11 | 50527.61 | -97.2% | -97.8% | -3435.9% | 30.0% | PASS | `----------------` |
| crossref_batch_fetch_200 | 1 | 0.24 | 0.33 | 837103.79 | 44.8% | 52.5% | 30.9% | 150.0% | PASS | `########--------` |
| silver_prepare_arrow_2000 | 1 | 2.11 | 2.25 | 949804.72 | -62.4% | -78.4% | -165.9% | 25.0% | PASS | `----------------` |
| silver_write_append_600 | 1 | 23.72 | 24.67 | 25293.19 | -11.5% | -41.3% | -13.0% | 60.0% | PASS | `----------------` |
| silver_write_merge_600 | 1 | 49.21 | 51.03 | 12192.21 | -13.5% | -28.2% | -15.6% | 70.0% | PASS | `----------------` |

