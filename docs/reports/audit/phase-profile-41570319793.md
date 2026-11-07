# Profiling Report: Collection/Fixtures Nightly 41570319793

**Run ID**: 41570319793 (attempt 1)
**Status**: PARTIAL / BLOCKED
**Blocker**: E:\backup\ci-stage0-20261103\ and raw-jobs-attempt-1.json are inaccessible in the sandbox environment. gh CLI and authorized GitHub Actions API access are unavailable.

## Top 10 Suites by Test-Time Sum

| Suite | Σ test-time (s) | Wall-time | Setup Σ | Call Σ | Teardown Σ | Remainder (Wall - Σ known) |
|---|---|---|---|---|---|---|
| tooling-other | 320.5 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE (not attribution) |
| integration | 233.2 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE (not attribution) |
| repo-backed-tooling | 125.6 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE (not attribution) |
| unit-domain | 118.8 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE (not attribution) |
| unit-infrastructure | 95.0 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE (not attribution) |
| unit-application | 74.5 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE (not attribution) |
| contract-confidence | 72.9 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE (not attribution) |
| unit-other | 70.9 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE (not attribution) |
| fast-unit-domain | 31.6 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE (not attribution) |
| fast-unit-application | 25.9 | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE (not attribution) |

*Note: Wall time, phase breakdowns (setup, call, teardown), and remainder are marked UNAVAILABLE because original job logs and raw-jobs data could not be accessed.*

## Instrumentation Candidates (Phase 1.1 / Stage 2)

Based on the available Σ testcase-time metrics, the following suites are recommended for instrumentation:

1. **tooling-other** (320.5s) - Largest test execution time. High priority for profiling to identify slow tests or bottlenecks.
2. **integration** (233.2s) - Second largest test execution time. Integration tests often have significant setup/teardown overhead, making them prime candidates for phase profiling.
3. **repo-backed-tooling** (125.6s) - Third largest execution time. Tooling tests with I/O or network operations are likely sources of high latency.

## Verification
- No repository, CI, thresholds, or baseline changes were made.
