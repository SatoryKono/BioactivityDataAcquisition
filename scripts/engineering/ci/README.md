# scripts/ci — CI Orchestration

CI orchestration, resiliency runners, and periodic quality reports.

## Unified Entry Point

```bash
python -m scripts.engineering.ci --help
python -m scripts.engineering.ci <command> [args...]
```

## Commands

| Command          | Script                                                 | Description                                                                 |
| ---------------- | ------------------------------------------------------ | --------------------------------------------------------------------------- |
| `run-tests`      | `scripts/engineering/ci/run_pytest_resilient.py`       | Run pytest with resilient retry logic                                       |
| `quality-gate`   | `scripts/engineering/ci/quality_integral_gate.py`      | Integral quality gate for CI with descriptive test-health classification    |
| `e2e-skip-rate`  | `scripts/engineering/ci/check_e2e_matrix_skip_rate.py` | Check E2E matrix skip rate against threshold                                |
| `e2e-rerun`      | `scripts/engineering/ci/check_e2e_rerun_stability.py`  | Check E2E rerun stability                                                   |
| `debt-report`    | `scripts/engineering/ci/report_quality_debt_weekly.py` | Generate weekly quality debt report                                         |
| `apply-ci-fixes` | `scripts/engineering/ci/apply_ci_fixes.py`             | One-off GitHub-hosted workflow repair helper requiring explicit token input |

## When to Use

| Command        | When                                                                                                                                                                                              | Trigger                                |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------- |
| `run-tests`    | Primary test execution in CI; wraps pytest with xdist parallelization and serial fallback on worker crashes                                                                                       | CI pipeline (automatic)                |
| `quality-gate` | Pre-merge quality validation; computes integral quality score, blocks PR if below quarterly target, and emits descriptive `fully exercised` / `staged` / `environment-limited` test-health status | CI gate (`architecture.yml`, every PR) |

Canonical taxonomy:

- descriptive test-health classes are defined in [configs/quality/test_health_reporting.yaml](../../../configs/quality/test_health_reporting.yaml)
- these classes are informational and do not replace merge-blocking CI pass/fail or the quality gate
- skip-conditioned buckets are also canonicalized there, so reports can distinguish architecture skips, network opt-in gating, scheduled live gates, pilot providers, and VCR-only providers
  | `e2e-skip-rate` | After E2E test runs; validates skip rate against SLO, classifies infra_flaky vs code_regression | CI gate (`e2e-matrix-health.yml`) |
  | `e2e-rerun` | After multi-run E2E validation; detects non-deterministic test outcomes across repeated runs | CI gate (`e2e-matrix-health.yml`) |
  | `debt-report` | Weekly debt tracking; generates architecture debt snapshot (JSON + Markdown) | Scheduled weekly (Monday 4:45 UTC) |
  | `apply-ci-fixes` | Exceptional maintenance only; applies pre-authored GitHub workflow fixes against the hosted repository via PAT | Manual, maintainer-only |

## Other Files

| File                                                      | Description                                                                   |
| --------------------------------------------------------- | ----------------------------------------------------------------------------- |
| `scripts/engineering/ci/apply-ci-optimizations.ps1`       | PowerShell CI optimization script                                             |
| `scripts/engineering/ci/apply-ci-optimizations-fixed.ps1` | Fixed variant of CI optimization                                              |
| `scripts/engineering/ci/_compatibility_registry.py`       | Shared compatibility registry loader used by telemetry/reporting helpers      |
| `scripts/engineering/ci/_compatibility_telemetry.py`      | Compatibility inventory telemetry helper used by architecture reporting flows |
