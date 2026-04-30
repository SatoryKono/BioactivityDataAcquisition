# Telemetry and Flaky DB Contract

## Raw event JSONL schema

Store events in:

- `reports/test-swarm/<task_id>/telemetry/raw/events_<agent_id>.jsonl`

Example:

```json
{
  "timestamp": "2026-02-26T12:00:00Z",
  "run_id": "SWARM-001-run-3",
  "agent_id": "L2-domain-unit",
  "agent_level": "L2",
  "shard_scope": "tests/unit/domain/",
  "test_nodeid": "tests/unit/domain/test_X.py::test_something",
  "test_type": "unit",
  "layer": "domain",
  "module": "domain.behavior.validation",
  "provider": null,
  "outcome": "fail",
  "error_type": "AssertionError",
  "normalized_error_signature": "assertion_validation_result_mismatch",
  "error_message": "expected 42, got 41",
  "traceback_head": "...",
  "duration_ms": 120,
  "retry_index": 2,
  "is_flaky_suspected": true,
  "git_sha": "abc1234"
}
```

Allowed `outcome` values:

- `pass`, `fail`, `error`, `skip`, `xfail`, `xpass`

## Aggregated outputs

Generate:

- `telemetry/aggregated/failure_stats.csv`
- `telemetry/aggregated/flaky_index.csv`
- `telemetry/failure_frequency_summary.md`

`failure_stats.csv` columns:

```text
test_nodeid,test_type,layer,module,provider,total_runs,pass_count,fail_count,
failure_frequency,flaky_index,error_signature,first_seen,last_seen
```

`flaky_index.csv` columns:

```text
test_nodeid,total_runs,intermittent_fails,flaky_index,triage_status,suspected_cause
```

## Alert thresholds

| Condition                | Alert    | Action                   |
| ------------------------ | -------- | ------------------------ |
| failure_frequency > 0.10 | Warning  | prioritize debug         |
| failure_frequency > 0.20 | Critical | mandatory fix/quarantine |
| flaky_index > 0.15       | Critical | mandatory stabilization  |

## Flakiness database (`flakiness-database.json`)

Top-level skeleton:

```json
{
  "task_id": "SWARM-001",
  "generated_at": "2026-02-26T12:00:00Z",
  "git_sha": "abc1234def5678",
  "total_runs_per_test": 5,
  "total_tests_analyzed": 0,
  "alert_thresholds": {
    "failure_frequency_warning": 0.1,
    "failure_frequency_critical": 0.2,
    "flaky_index_critical": 0.15
  },
  "flaky_tests": [],
  "summary": {
    "total_flaky": 0,
    "by_layer": {},
    "by_category": {},
    "by_severity": {},
    "by_triage": {},
    "by_alert_level": {}
  },
  "root_cause_clusters": []
}
```

Each flaky test item should include:

- test ID and classification (`layer`, `module`, `provider`, `test_type`)
- run statistics (`total_runs`, pass/fail/error counts)
- flakiness rate and alert level
- triage status (`fixed | quarantined | manual-review`)
- failure reasons with normalized signatures
- severity, suspected cause, recommended fix, first seen, fixed flag

## Summary expectations (`failure_frequency_summary.md`)

Include:

1. Top-20 unstable tests
1. Layer/module heatmap (text table)
1. deterministic vs flaky split
1. root-cause clusters by `normalized_error_signature`
1. duration vs failure-probability observations
1. delta vs `baseline_report` (if provided)
