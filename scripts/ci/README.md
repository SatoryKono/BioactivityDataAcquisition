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

## Other Files

| File | Description |
|------|-------------|
| `apply-ci-optimizations.ps1` | PowerShell CI optimization script |
| `apply-ci-optimizations-fixed.ps1` | Fixed variant of CI optimization |
