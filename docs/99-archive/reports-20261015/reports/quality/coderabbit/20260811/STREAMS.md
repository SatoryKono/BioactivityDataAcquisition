# Implementation streams — CR-FULL 20260811

Exclusive streams for accepted (`confirm`) findings only.
Phase 5 implementation requires separate authorization.

| Stream | Issue | Findings | Priority | Scope |
|---|---:|---:|---|---|
| `domain-behavior` | #8643 | 37 | P1 | {'major': 19, 'minor': 15, 'critical': 2, 'trivial': 1} |
| `domain-other` | #8644 | 31 | P1 | {'major': 21, 'minor': 9, 'critical': 1} |
| `domain-aggregates` | #8645 | 3 | P1 | {'major': 3} |

## Ordering recommendation

1. Stream A `domain-aggregates` (3 major) — batch/quarantine/pipeline_run defects
2. Stream B `domain-behavior` (37) — validators/DQ/HTML serialization
3. Stream C `domain-other` (31) — remaining domain packages from successful leaves

Do not mix streams in one PR. One independent behavior change per task.
