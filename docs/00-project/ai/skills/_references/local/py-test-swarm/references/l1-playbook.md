# L1 Playbook (py-test-swarm)

Runtime note:

- CI or single-OS checkout: keep the `uv run python -m ...` commands below as-is.
- Windows PowerShell in a mixed checkout: use `.\scripts\engineering\dev\run_pytest.ps1` / `.\scripts\engineering\dev\run_mypy.ps1` or `.\.venv-win\Scripts\python.exe -m ...`.
- WSL/Linux in a mixed checkout: use `bash scripts/engineering/dev/run_pytest.sh` / `bash scripts/engineering/dev/run_mypy.sh` or `"${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}/bin/python" -m ...`.

## 1) Discovery (mandatory before delegation)

```bash
# 1. Baseline snapshot
uv run python -m pytest tests/ -v --tb=short -q 2>&1 | tail -50

# 2. Coverage snapshot
uv run python -m pytest tests/ --cov=src/bioetl --cov-report=term-missing --tb=no -q 2>&1 | tail -80

# 3. Failed tests list
uv run python -m pytest tests/ -v --tb=line -q 2>&1 | grep "FAILED" | sort

# 4. Architecture tests
uv run python -m pytest tests/architecture/ -v --tb=short -q 2>&1 | tail -30

# 5. Type check
uv run python -m mypy --strict src/bioetl/ 2>&1 | tail -20

# 6. Test inventory
uv run python -m pytest tests/ --collect-only -q 2>&1 | tail -5

# 7. Slowest tests
uv run python -m pytest tests/ --durations=20 -q 2>&1 | head -30
```

## 2) Workload score

```text
workload_score = files_count * complexity_factor * failing_factor * coverage_gap_factor
```

- `files_count`: Python files in scope (source + tests)
- `complexity_factor`: 1.0 low, 1.5 medium, 2.0 high
- `failing_factor`: `1 + (fail_ratio * 2)`
- `coverage_gap_factor`: `1 + gap` (gap in range 0.0-1.0)

Decision:

- `< 40`: Small, self-execute
- `40-89`: Medium, spawn 2-3 child agents
- `>= 90`: Large, spawn 4-6 child agents

Fallback delegation triggers:

- test files `> 30`
- failed tests `> 15`
- untested modules `> 10`
- estimated runtime `> 20 minutes`
- flaky rate `> 10%` (spawn dedicated flaky triage agent)

## 3) Standard L2 decomposition

| #   | L2 Agent ID         | Scope                                                                  | Test type          | Priority |
| --- | ------------------- | ---------------------------------------------------------------------- | ------------------ | -------- |
| 1   | L2-domain-unit      | tests/unit/domain/                                                     | unit               | P1       |
| 2   | L2-app-unit         | tests/unit/application/                                                | unit               | P1       |
| 3   | L2-infra-unit-integ | tests/unit/infrastructure/ + tests/integration/                        | unit + integration | P1       |
| 4   | L2-comp-iface-unit  | tests/unit/composition/ + tests/unit/interfaces/                       | unit               | P2       |
| 5   | L2-crosscutting     | tests/architecture/ + tests/e2e/ + tests/contract/ + tests/benchmarks/ | mixed              | P2       |

Execution order:

- `L2-domain-unit || L2-crosscutting`
- `L2-app-unit || L2-infra-unit-integ`
- `L2-comp-iface-unit` after domain+app
- max 4 concurrent L2 agents

## 4) Plan file contract (`00-swarm-plan.md`)

Must contain:

- task metadata (`task_id`, date, mode, scope)
- baseline metrics table (total/pass/fail/skip/error, coverage overall/domain, arch tests, mypy, timings)
- L2 decomposition table with estimated files and workload score
- execution order and parallelism constraints

## 5) L1 aggregation checklist

1. Read all child `report.md` and `metrics.json`.
1. Merge `telemetry/raw/*.jsonl`.
1. Build:

- `telemetry/aggregated/failure_stats.csv`
- `telemetry/aggregated/flaky_index.csv`
- `telemetry/failure_frequency_summary.md`
- `flakiness-database.json`

4. Generate `FINAL-REPORT.md`.
1. Mark unresolved claims as `Requires Manual Review`.
