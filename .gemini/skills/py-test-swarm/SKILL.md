______________________________________________________________________

## name: py-test-swarm description: Orchestrate hierarchical BioETL test swarms (L1/L2/L3) for full_audit, fix_failures, coverage_boost, optimize, and flakiness_scan with workload-based delegation, telemetry aggregation, flaky analysis, and final reporting in `reports/{LLM}/review_py-test-swarm_{YYYYMMDD}_{HHMM}_FINAL.md`. Use when users request broad test campaigns, failure triage at scale, coverage expansion, or stability diagnostics across layers/providers.

# py-test-swarm

## Core Role

Act as L1 orchestrator by default.
Decompose work into L2/L3 agents, enforce constraints, aggregate evidence, and produce final artifacts.

## Startup Sequence

1. Start with the canonical memory loop from `../../../src/memory/DAILY_WORKFLOW.md` and run `python -m memory.tooling.workflow pre-task ...` for the swarm task.
1. Read `../../../docs/00-project/ai/agents/guides/MEMORY_USAGE.md` before
   consuming memory sheets.
1. Read memory:

- `../../../docs/00-project/ai/memory/agent-memory.md`
- `../../../docs/00-project/ai/memory/memory-py-test-bot.md`
- `../../../.gemini/agents/ORCHESTRATION.md` (sections 2-7)
- There is no dedicated `memory-py-test-swarm.md` sheet today; use
  `agent-memory.md` plus `memory-py-test-bot.md` and record that fallback in
  the report when it matters.

3. Read profile:

- `../../../.gemini/agents/py-test-swarm.md`

4. Confirm input contract:

- `task_id` (required)
- `mode` (required): `full_audit | fix_failures | coverage_boost | optimize | flakiness_scan`
- `scope` (optional, default all tests)
- `baseline_report` (optional)
- `flakiness_runs` (optional, default `5`)

5. Create artifact root: `reports/{LLM}/py-test-swarm_{YYYYMMDD}_{HHMM}/` (LLM = caller).

## Cross-Platform Runtime Note

- CI or single-OS checkout: `uv run python -m ...`
- Windows PowerShell in a mixed checkout: `.\scripts\dev\run_pytest.ps1`, `.\scripts\dev\run_mypy.ps1`, or `.\.venv-win\Scripts\python.exe -m ...`
- WSL/Linux in a mixed checkout: `bash scripts/dev/run_pytest.sh`, `bash scripts/dev/run_mypy.sh`, or `"${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}/bin/python" -m ...`

## L1 Workflow

1. Run Discovery baseline commands from [l1-playbook.md](references/l1-playbook.md).
1. Build `00-swarm-plan.md` with workload scores and parallel execution plan.
1. Launch L2 agents with full task brief template from [l2-l3-task-brief.md](references/l2-l3-task-brief.md).
1. Limit concurrent L2 agents to 4; run independent scopes in parallel.
1. Collect all L2/L3 `report.md`, `metrics.json`, and telemetry JSONL.
1. Build aggregated telemetry and flaky DB using [telemetry-and-flaky-db.md](references/telemetry-and-flaky-db.md).
1. Produce `FINAL-REPORT.md` from [report-templates.md](references/report-templates.md).

## Decomposition Model

Use three axes:

- Architecture layers: `domain`, `application`, `infrastructure`, `composition`, `interfaces`
- Test types: `unit`, `integration`, `e2e`, `architecture`, `contract`, `smoke`, `performance`, `security`
- Infrastructure zones: adapters/providers, transformation, storage, DQ, retry/circuit-breaker, checkpoint/locking/heartbeat, observability, CLI

## Delegation Rules

Calculate:

```text
workload_score = files_count * complexity_factor * failing_factor * coverage_gap_factor
```

Decision:

- `< 40`: self-execute
- `40-89`: delegate to 2-3 child agents
- `>= 90`: delegate to 4-6 child agents

Fallback delegation triggers (if formula is not practical):

- test files in scope `> 30`
- failing tests `> 15`
- modules without tests `> 10`
- estimated runtime `> 20 min`
- flaky rate `> 10%` (spawn dedicated flaky triage agent)

Hierarchy limit: `L1 -> L2 -> L3` only.

## L2/L3 Protocol

L2 and L3 must follow 6 phases:

- Phase 0: discovery and workload scoring
- Phase 1: stabilization
- Phase 2: coverage expansion
- Phase 3: optimization
- Phase 4: telemetry/flakiness scan
- Phase 5: reporting

For L3 agents always prepend the mandatory leaf-agent instruction from [l2-l3-task-brief.md](references/l2-l3-task-brief.md).

## Artifact Contract

Minimum required outputs:

- `reports/{LLM}/py-test-swarm_{YYYYMMDD}_{HHMM}/00-swarm-plan.md`
- `reports/{LLM}/py-test-swarm_{YYYYMMDD}_{HHMM}/L2-*/report.md`
- `reports/{LLM}/py-test-swarm_{YYYYMMDD}_{HHMM}/L2-*/metrics.json`
- `reports/{LLM}/py-test-swarm_{YYYYMMDD}_{HHMM}/telemetry/raw/events_*.jsonl`
- `reports/{LLM}/py-test-swarm_{YYYYMMDD}_{HHMM}/telemetry/aggregated/failure_stats.csv`
- `reports/{LLM}/py-test-swarm_{YYYYMMDD}_{HHMM}/telemetry/aggregated/flaky_index.csv`
- `reports/{LLM}/py-test-swarm_{YYYYMMDD}_{HHMM}/telemetry/failure_frequency_summary.md`
- `reports/{LLM}/py-test-swarm_{YYYYMMDD}_{HHMM}/flakiness-database.json`
- `reports/{LLM}/review_py-test-swarm_{YYYYMMDD}_{HHMM}_FINAL.md`

## Constraints

MUST:

- Keep architecture boundaries and no I/O in domain.
- Use the OS-appropriate command path: `uv run python -m ...` in CI/single-OS, `.\scripts\dev\run_pytest.ps1` / `.\scripts\dev\run_mypy.ps1` in PowerShell, and `bash scripts/dev/run_pytest.sh` / `bash scripts/dev/run_mypy.sh` in WSL.
- Keep swarm changes in tests/reporting artifacts; do not modify production code unless explicitly requested outside swarm.
- Use VCR/respx for HTTP tests; keep secrets out of cassettes.
- Add regression tests for fixed failures when fixes are applied.
- Provide evidence (`file + lines + command`) for architectural claims.

MUST NOT:

- Remove tests without rationale.
- Hide failures via unjustified `skip`.
- Add test-only logic in `src/bioetl/`.
- Exceed L3 depth.
- Leak secrets in logs/reports/cassettes.

## Mode Matrix

- `full_audit`: phases 0-5
- `fix_failures`: phases 0-1
- `coverage_boost`: phases 0 and 2
- `optimize`: phases 0 and 3
- `flakiness_scan`: phases 0 and 4

## Completion Criteria

Treat task as done only when:

- all active agents wrote `report.md` and `metrics.json`;
- L2 orchestrators aggregated L3 reports (if any);
- L1 generated `FINAL-REPORT.md`;
- telemetry aggregates + flaky DB are generated;
- unresolved assumptions are explicitly marked `Requires Manual Review`.
- after closeout, run `python -m memory.tooling.workflow post-task ...` and promote only durable testing lessons or incident knowledge.

## References

- L1 runbook and command sequence: [l1-playbook.md](references/l1-playbook.md)
- L2/L3 task briefs and prompt templates: [l2-l3-task-brief.md](references/l2-l3-task-brief.md)
- Report and metrics templates: [report-templates.md](references/report-templates.md)
- Telemetry schema and flaky DB contract: [telemetry-and-flaky-db.md](references/telemetry-and-flaky-db.md)
