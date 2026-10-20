# Benchmark Provenance Report

| N | SHA | Command | Wall Time | Merge Time Sum | Peak RSS | Rows (Lines) |
|---|---|---|---|---|---|---|
| 10 | 1117a76a578cc7315cfe62823b8d5d7c6759b2af | `/usr/bin/time -v uv run pytest tests/performance/test_delta_sequential_merge.py::test_delta_sequential_merge_scaling[10] --delta-merge-report-dir=./reports/performance/evidence/1117a76a578cc7315cfe62823b8d5d7c6759b2af/run_1/N10` | 0:04.25 | 0.6745s | 332692 KB | 4100 |
| 50 | 1117a76a578cc7315cfe62823b8d5d7c6759b2af | `/usr/bin/time -v uv run pytest tests/performance/test_delta_sequential_merge.py::test_delta_sequential_merge_scaling[50] --delta-merge-report-dir=./reports/performance/evidence/1117a76a578cc7315cfe62823b8d5d7c6759b2af/run_1/N50` | 0:09.07 | 5.0456s | 369460 KB | 20100 |
| 100 | 1117a76a578cc7315cfe62823b8d5d7c6759b2af | `/usr/bin/time -v uv run pytest tests/performance/test_delta_sequential_merge.py::test_delta_sequential_merge_scaling[100] --delta-merge-report-dir=./reports/performance/evidence/1117a76a578cc7315cfe62823b8d5d7c6759b2af/run_1/N100` | 0:18.76 | 13.9380s | 442444 KB | 40100 |
