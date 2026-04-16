# Failure Frequency Summary

## Analytics

- 2 flaky tests detected in `infrastructure.adapters` module.

### Top 20 Flaky Tests
| Test | Frequency | Flaky Index | Category | Status | Suggested Fix |
|------|-----------|-------------|----------|--------|---------------|
| `test_flaky_infra_1` | 20% | 20% | Infrastructure | quarantined | Retry network calls |
| `test_flaky_infra_2` | 20% | 20% | Infrastructure | quarantined | Retry network calls |

### Root-cause clusters
- `network_timeout`: 2 instances in `infra.adapters`
