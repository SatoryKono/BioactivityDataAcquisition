# Report Templates

## L2/L3 `report.md`

```markdown
# Test Report: {scope_description}

**Date**: YYYY-MM-DD HH:MM
**Agent ID**: {agent_id}
**Agent Level**: L2 | L3
**Scope**: {test_paths}
**Source**: {source_paths}

## Summary
| Metric | Before | After | Delta | Status |
|--------|:------:|:-----:|:-----:|:------:|
| Total tests | N | N | +N | |
| Passed | N | N | +N | |
| Failed | N | N | -N | |
| Coverage | N% | N% | +N% | |
| Flaky tests | N | N | -N | |
| Median time | Ns | Ns | -Ns | |
| p95 time | Ns | Ns | -Ns | |

## Fixed Tests
| # | Test ID | Category | Root Cause | Fix | Evidence |
|:-:|---------|----------|------------|-----|----------|
| 1 | ... | ... | ... | ... | `file.py:42` |

## Regression Tests Added
| # | Test | Covers Bug | File |
|:-:|------|-----------|------|
| 1 | ... | ... | ... |

## New Tests Created
| # | File | Tests Added | Covers Module | Coverage Delta |
|:-:|------|:-----------:|---------------|:--------------:|
| 1 | ... | N | ... | +N% |

## Optimized Tests
| # | Test ID | Before | After | Optimization |
|:-:|---------|:------:|:-----:|-------------|
| 1 | ... | 8.2s | 1.1s | fixture scope |

## Flaky Tests Detected
| # | Test ID | Flakiness Rate | Triage Status | Suspected Cause |
|:-:|---------|:--------------:|:-------------:|-----------------|
| 1 | ... | 20% | quarantined | shared state |

## Remaining Issues
| # | Test ID | Issue | Severity | Suggested Action |
|:-:|---------|-------|:--------:|-----------------|
| 1 | ... | ... | P2 | manual review |

## Evidence (commands)
- `uv run python -m pytest ...` / `uv run python -m mypy --strict ...` (CI or single-OS checkout)
- `.\scripts\dev\run_pytest.ps1 ...` / `.\scripts\dev\run_mypy.ps1 ...` (Windows PowerShell mixed checkout)
- `bash scripts/engineering/dev/run_pytest.sh ...` / `bash scripts/engineering/dev/run_mypy.sh ...` (WSL/Linux mixed checkout)

## Risks & Requires Manual Review
- ...

## L3 Agent Reports (for L2 orchestrators only)
| # | L3 Agent | Scope | Status | Key Findings |
|:-:|----------|-------|:------:|-------------|
| 1 | ... | ... | DONE | ... |
```

## `metrics.json`

```json
{
  "agent_id": "L2-domain-unit",
  "level": "L2",
  "scope": "tests/unit/domain/",
  "status": "completed",
  "overall_status": "GREEN",
  "metrics_before": {
    "total_tests": 0,
    "passed": 0,
    "failed": 0,
    "skipped": 0,
    "coverage_pct": 0.0,
    "median_duration_ms": 0,
    "p95_duration_ms": 0
  },
  "metrics_after": {
    "total_tests": 0,
    "passed": 0,
    "failed": 0,
    "skipped": 0,
    "coverage_pct": 0.0,
    "median_duration_ms": 0,
    "p95_duration_ms": 0
  },
  "actions": {
    "tests_fixed": 0,
    "tests_added": 0,
    "tests_optimized": 0,
    "flaky_found": 0,
    "flaky_fixed": 0,
    "flaky_quarantined": 0
  },
  "top_failures": [],
  "files_changed": [],
  "recommendations": []
}
```

## `FINAL-REPORT.md` skeleton (L1)

```markdown
# BioETL Test Swarm Final Report

**Task ID**: <task_id>
**Date**: YYYY-MM-DD HH:MM
**Mode**: <mode>
**Duration**: <duration>
**Overall Status**: GREEN | YELLOW | RED
**Agent Tree**: L1 -> N*L2 -> M*L3

## Executive Summary
<2-3 sentences>

## Overall Metrics (Before/After)
<table>

## Coverage by Layer
<table>

## Coverage by Provider
<table>

## Test Type Distribution
<table>

## Agent Hierarchy Summary
<table>

## Agent Execution Log
<tree-like text>

## Top Fixed Tests
<table>

## Top Failure Frequency
<table>

## Root-Cause Clusters
<table>

## Coverage Gaps
<table>

## Stability Score
<table>

## Prioritized Remediation Backlog
### P1
### P2
### P3

## CI Optimization Recommendations
1. ...
2. ...
3. ...

## Appendix
- flakiness-database.json
- telemetry/failure_frequency_summary.md
- telemetry/raw/
```
