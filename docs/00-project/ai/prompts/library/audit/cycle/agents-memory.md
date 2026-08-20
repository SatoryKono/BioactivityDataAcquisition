---
id: prompt.audit.cycle.agents-memory
version: 1.1.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [grok, codex, any]
params:
  - N
  - SCOPE
  - MODE
  - LANGUAGE
  - AUDIT_MODE
  - CONTOURS
  - ALLOW_ISSUE_WRITE
  - ALLOW_PUSH
  - ALLOW_MERGE
  - ALLOW_CLOSE
  - MAX_ISSUES_PER_ITERATION
  - BASE_BRANCH
  - REPO
includes:
  - fragments/read-order.md
  - fragments/git-safety.md
  - fragments/debt-budget-ban.md
  - fragments/env-guardrail.md
  - fragments/evidence-contract.md
  - fragments/language-ru.md
  - fragments/audit-scale.md
  - fragments/finding-schema.md
  - fragments/project-requirements-audit.md
  - fragments/unknown-params.md
  - fragments/reports-output.md
  - fragments/shell-portability.md
  - fragments/orchestrator-guards.md
related_ssot:
  - AGENTS.md
  - docs/00-project/NORMATIVE_SOURCES.md
  - docs/01-requirements/REQUIREMENTS.md
  - docs/01-requirements/traceability/requirements-traceability-crosswalk.csv
  - docs/00-project/ai/agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md
  - docs/00-project/ai/agents/guides/MEMORY_USAGE.md
  - docs/00-project/ai/prompts/README.md
  - src/memory/DAILY_WORKFLOW.md
  - .codex/agents
  - .junie/agents
  - docs/00-project/ai/prompts/library/audit/agents-runtime.md
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
anti_patterns:
  - Inventing REQ-* IDs not in REQUIREMENTS.md / the traceability CSV
  - Treating the Prompt Library as runtime SSOT
  - Ignoring .codex / .junie / .devin discovery
  - Auto-running destructive agent scripts
  - Conversation dumps or secrets in memory handoffs
  - Fixing only a docs mirror without a runtime plan
  - Empty form cycles
tags: [audit, agents, memory, runtime, scripts, cycle, operator]
summary: Cyclic audit of AI runtime, agent scripts, and agent memory
max_body_lines: 250
---

# Cyclic agents + memory audit

N-итерационный аудит **инструкций агентов, вспомогательных скриптов и памяти**.
Runtime SSOT = `.codex/**` ≡ `.junie/**` (+ `.devin/**` when present).
Prompt Library — operator aid only. Memory ≠ runtime truth.

Domain method: `prompt.audit.agents-runtime` plus memory workflow below.
Loop shell: `prompt.audit.orchestrator`. Default **`N=10`**, **`MODE=full`**,
**`CONTOURS=runtime,scripts,memory`**, все **`ALLOW_*=true`**.

## Params

| Param | Default |
| --- | --- |
| `N` | `10` |
| `SCOPE` | `AGENTS.md .codex/ .junie/ .devin/ docs/00-project/ai/ scripts/ai/ src/memory/ scripts/memory/` |
| `MODE` | `full` (`audit` \| `audit+issues` \| `full`) |
| `LANGUAGE` | `ru` |
| `AUDIT_MODE` | `full` \| `differential` |
| `CONTOURS` | `runtime,scripts,memory` |
| `ALLOW_ISSUE_WRITE` | `true` |
| `ALLOW_PUSH` | `true` |
| `ALLOW_MERGE` | `true` |
| `ALLOW_CLOSE` | `true` |
| `MAX_ISSUES_PER_ITERATION` | `5` |
| `BASE_BRANCH` | `main` |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |

## BioETL anchors

- Requirements: `docs/01-requirements/REQUIREMENTS.md` + traceability CSV; PROVEN findings need `requirement_id`
- Precedence: `AGENTS.md` → `AI_RUNTIME_MIRROR_OWNERSHIP.md`
- Parity: `bash scripts/ai/junie/check_junie_mirror.sh --check`
- Memory: `MEMORY_USAGE.md`, `src/memory/DAILY_WORKFLOW.md`
- Workflow: `python -m memory.tooling.workflow pre-task|post-task|smoke`
- Helper: `bash scripts/memory/run_workflow.sh …` (venv + `PYTHONPATH=src`)
- Catalog / policy / schemas: `src/memory/catalog/`, `src/memory/policy/`,
  `src/memory/schemas/`
- Actor provenance: `BIOETL_AI_RUNTIME`, `BIOETL_AI_AGENT` (optional `BIOETL_AI_MODEL`)
- Neo4j / MCP memory is optional (ADR-010). Degraded retrieval ≠ skip catalog verify.
- Windows: `.\.venv-win\Scripts\python.exe`

## Preflight

1. `git status --porcelain`; SHA; branch. Foreign dirty work → worktree.
2. Confirm SCOPE paths exist; empty SCOPE → STOP.
3. `run_id = <UTC>-agents-memory-cycle-<shortsha>`
4. Artifacts: `reports/audit-runs/<run_id>/` + mirror `reports/audit/agents/`.

## Iteration i = 1..N

Run only contours listed in `CONTOURS`.

| Phase | Action |
| --- | --- |
| **A Runtime** | Inventory `AGENTS.md`, `.codex/agents/**`, `.codex/skills/**`, `.junie/**`, `.devin/**`, `docs/00-project/ai/**` (mirrors). Build instruction scope graph: root → profile → skill → scripts → CI. Flag contradictions (commands, versions, write vs read-only). |
| **B Scripts** | `scripts/ai/**`, `scripts/memory/**`. Idempotency, dry-run for destructive ops, non-zero on failure, no `curl\|bash`, no unquoted sinks, no secret-on-stdout. Validate bootstrap/test commands against manifests. |
| **C Memory** | Catalog ↔ schema. Smoke `python -m memory.tooling.workflow smoke` (or `run_workflow.sh smoke`). Check actor provenance, promote-only durable knowledge, no secrets in notes/handoffs, no full conversation dumps. Vendor registry stays `NOT_PROVEN` without dated evidence. |
| **D Plan / Issues** | Cluster by contour. Create if ALLOW_ISSUE_WRITE + PROVEN + `requirement_id`. Title `[agents][<REQ-id>][P#]`. Do not fix runtime via docs-mirror only. |
| **E Fix** | Runtime source first, then mirrors. Memory: tooling/policy/docs only. Never raise debt limits in memory sheets. No `.env` edits. |
| **F Validate** | Re-run `check_junie_mirror.sh --check` if `.codex`/`.junie` changed. Re-smoke memory workflow. Delta: resolved / unchanged / regressed / new. |

## Focus checklist (each cycle)

- [ ] Instruction graph has no command/version contradictions
- [ ] `.codex` ↔ `.junie` parity checked when those trees are in SCOPE
- [ ] Docs mirrors do not redefine runtime behavior
- [ ] Agent scripts fail closed; destructive ops have dry-run
- [ ] Memory catalog validates against schemas
- [ ] Handoffs have no secrets and no full transcripts
- [ ] `BIOETL_AI_RUNTIME` / `BIOETL_AI_AGENT` required for durable records
- [ ] Debt-budget ban preserved in memory sheets

## Stop

Script that can leak secrets or destroy data without a guard → P0.
Conversation dump or secret in a memory artifact → P0 + stop leak.
Empty SCOPE → STOP. Fix-only-in-mirror without runtime plan → STOP.

## Success

- `findings.json` + `report.md` under `reports/audit-runs/<run_id>/`
- Contours in `CONTOURS` each have evidence
- Mirror check + memory smoke recorded when those trees changed
- `surface_score` 0–3; cap at 1 if any P0 remains

## Related

- One-shot: `prompt.audit.agents-runtime`
- Dual-agent: `prompt.audit.dual-agent-cycle` +
  `AUDIT_PROMPT_SOURCE=prompt.audit.agents-runtime`
- Closeout: `prompt.closeout.grok`
- Previous: `prompt.audit.cycle.diagrams` · Next: `prompt.audit.cycle.configs`
