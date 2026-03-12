# scripts/ci — CI Orchestration

CI orchestration, resiliency runners, and periodic quality reports.

## Unified Entry Point

```bash
python -m scripts.ci --help
python -m scripts.ci <command> [args...]
```

## Commands

| Command | Script | Description |
|---------|--------|-------------|
| `run-tests` | `run_pytest_resilient.py` | Run pytest with resilient retry logic |
| `quality-gate` | `quality_integral_gate.py` | Integral quality gate for CI |
| `e2e-skip-rate` | `check_e2e_matrix_skip_rate.py` | Check E2E matrix skip rate against threshold |
| `e2e-rerun` | `check_e2e_rerun_stability.py` | Check E2E rerun stability |
| `debt-report` | `report_quality_debt_weekly.py` | Generate weekly quality debt report |

## When to Use

| Command | When | Trigger |
|---------|------|---------|
| `run-tests` | Primary test execution in CI; wraps pytest with xdist parallelization and serial fallback on worker crashes | CI pipeline (automatic) |
| `quality-gate` | Pre-merge quality validation; computes integral quality score, blocks PR if below quarterly target | CI gate (`architecture.yml`, every PR) |
| `e2e-skip-rate` | After E2E test runs; validates skip rate against SLO, classifies infra_flaky vs code_regression | CI gate (`e2e-matrix-health.yml`) |
| `e2e-rerun` | After multi-run E2E validation; detects non-deterministic test outcomes across repeated runs | CI gate (`e2e-matrix-health.yml`) |
| `debt-report` | Weekly debt tracking; generates architecture debt snapshot (JSON + Markdown) | Scheduled weekly (Monday 4:45 UTC) |

## Other Files

| File | Description |
|------|-------------|
| `apply-ci-optimizations.ps1` | PowerShell CI optimization script |
| `apply-ci-optimizations-fixed.ps1` | Fixed variant of CI optimization |
