# Telemetry and Flaky DB Contract

## Raw event JSONL schema

Store events in:
- `reports/test-swarm/<task-id>/telemetry/raw/events-<agent-id>.jsonl`

Example:

```json
{
  "timestamp": "2026-02-26T12:00:00Z",
  "run-id": "SWARM-001-run-3",
  "agent-id": "L2-domain-unit",
  "agent-level": "L2",
  "shard-scope": "tests/unit/domain/",
  "test-nodeid": "tests/unit/domain/test-X.py::test-something",
  "test-type": "unit",
  "layer": "domain",
  "module": "domain.services.validation",
  "provider": null,
  "outcome": "fail",
  "error-type": "AssertionError",
  "normalized-error-signature": "assertion-validation-result-mismatch",
  "error-message": "expected 42, got 41",
  "traceback-head": "...",
  "duration-ms": 120,
  "retry-index": 2,
  "is-flaky-suspected": true,
  "git-sha": "abc1234"
}
```

Allowed `outcome` values:
- `pass`, `fail`, `error`, `skip`, `xfail`, `xpass`

## Aggregated outputs

Generate:
- `telemetry/aggregated/failure-stats.csv`
- `telemetry/aggregated/flaky-index.csv`
- `telemetry/failure-frequency-summary.md`

`failure-stats.csv` columns:

```text
test-nodeid,test-type,layer,module,provider,total-runs,pass-count,fail-count,
failure-frequency,flaky-index,error-signature,first-seen,last-seen
```

`flaky-index.csv` columns:

```text
test-nodeid,total-runs,intermittent-fails,flaky-index,triage-status,suspected-cause
```

## Alert thresholds

| Condition | Alert | Action |
|-----------|-------|--------|
| failure-frequency > 0.10 | Warning | prioritize debug |
| failure-frequency > 0.20 | Critical | mandatory fix/quarantine |
| flaky-index > 0.15 | Critical | mandatory stabilization |

## Flakiness database (`flakiness-database.json`)

Top-level skeleton:

```json
{
  "task-id": "SWARM-001",
  "generated-at": "2026-02-26T12:00:00Z",
  "git-sha": "abc1234def5678",
  "total-runs-per-test": 5,
  "total-tests-analyzed": 0,
  "alert-thresholds": {
    "failure-frequency-warning": 0.1,
    "failure-frequency-critical": 0.2,
    "flaky-index-critical": 0.15
  },
  "flaky-tests": [],
  "summary": {
    "total-flaky": 0,
    "by-layer": {},
    "by-category": {},
    "by-severity": {},
    "by-triage": {},
    "by-alert-level": {}
  },
  "root-cause-clusters": []
}
```

Each flaky test item should include:
- test ID and classification (`layer`, `module`, `provider`, `test-type`)
- run statistics (`total-runs`, pass/fail/error counts)
- flakiness rate and alert level
- triage status (`fixed | quarantined | manual-review`)
- failure reasons with normalized signatures
- severity, suspected cause, recommended fix, first seen, fixed flag

## Summary expectations (`failure-frequency-summary.md`)

Include:
1. Top-20 unstable tests
2. Layer/module heatmap (text table)
3. deterministic vs flaky split
4. root-cause clusters by `normalized-error-signature`
5. duration vs failure-probability observations
6. delta vs `baseline-report` (if provided)
