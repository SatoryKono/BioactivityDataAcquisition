# Benchmark Provenance Report

| N | SHA | Command | Wall Time | Merge Time Sum | Peak RSS | Final Rows | Processed Rows |
|---|---|---|---|---|---|---|---|
| 10 | 1117a76a578cc7315cfe62823b8d5d7c6759b2af | `/usr/bin/time -v uv run pytest tests/performance/test_delta_sequential_merge.py::test_delta_sequential_merge_scaling[10] --delta-merge-report-dir=./reports/performance/evidence/1117a76a578cc7315cfe62823b8d5d7c6759b2af/run_1/N10` | 0:04.25 | 0.6745s | 332692 KB | 4100 | 5000 |
| 50 | 1117a76a578cc7315cfe62823b8d5d7c6759b2af | `/usr/bin/time -v uv run pytest tests/performance/test_delta_sequential_merge.py::test_delta_sequential_merge_scaling[50] --delta-merge-report-dir=./reports/performance/evidence/1117a76a578cc7315cfe62823b8d5d7c6759b2af/run_1/N50` | 0:09.07 | 5.0456s | 369460 KB | 20100 | 25000 |
| 100 | 1117a76a578cc7315cfe62823b8d5d7c6759b2af | `/usr/bin/time -v uv run pytest tests/performance/test_delta_sequential_merge.py::test_delta_sequential_merge_scaling[100] --delta-merge-report-dir=./reports/performance/evidence/1117a76a578cc7315cfe62823b8d5d7c6759b2af/run_1/N100` | 0:18.76 | 13.9380s | 442444 KB | 40100 | 50000 |

## Evidence availability

The original full `/usr/bin/time -v` output and capture-time revision manifest
were not retained for `run_1`. Its wall-time/RSS values and SHA above are
historical claims, not independently verifiable raw evidence. They have not
been reconstructed or replaced.

A fresh capture from a clean checkout of the same source revision is stored
separately in `../run_2/benchmark_provenance.md`, with full timing output and
SHA-256 artifact bindings in `../run_2/manifest.json`. These are new measurements.

To capture future runs from a clean source checkout using its prepared Python
environment, run `python /path/to/scripts/engineering/performance/capture_delta_merge.py
--output-dir /path/to/new/run`. The tool verifies `GITHUB_SHA` against HEAD when
set, saves raw timing and pytest logs for each N, and generates the table from
the measured JSON summaries. Local runs record `github_sha: null` and bind
the source through `git rev-parse HEAD` instead.
