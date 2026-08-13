---
id: prompt.audit.coderabbit-project-cycle
version: 1.0.0
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
  - CODERABBIT
  - CR_MODE
  - INCLUDE_DOMAINS
  - MAX_FILES_PER_SCOPE
  - MAX_ISSUES_PER_ITERATION
  - MAX_WAVES_PER_ITERATION
  - ALLOW_ISSUE_WRITE
  - ALLOW_PUSH
  - ALLOW_MERGE
  - ALLOW_CLOSE
  - BASE_BRANCH
  - REPO
  - WORK_BRANCH
includes:
  - fragments/read-order.md
  - fragments/git-safety.md
  - fragments/debt-budget-ban.md
  - fragments/env-guardrail.md
  - fragments/evidence-contract.md
  - fragments/language-ru.md
  - fragments/audit-scale.md
  - fragments/finding-schema.md
  - fragments/unknown-params.md
  - fragments/reports-output.md
  - fragments/shell-portability.md
  - fragments/orchestrator-guards.md
  - fragments/coderabbit-dual-pass.md
related_ssot:
  - AGENTS.md
  - docs/00-project/NORMATIVE_SOURCES.md
  - docs/00-project/RULES.md
  - docs/03-guides/coderabbit-audit-playbook.md
  - docs/03-guides/development/coderabbit-local-reviews.md
  - .coderabbit.yaml
  - .github/workflows/coderabbit.yml
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
  - docs/00-project/ai/prompts/library/audit/cyclic-pack.md
  - docs/00-project/ai/prompts/library/audit/dual-agent-cycle.md
  - docs/00-project/ai/prompts/library/architecture/architecture-cycle.md
  - reports/quality/architecture-quality-scorecard.json
  - reports/quality/debt-governance-gates.json
  - docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md
anti_patterns:
  - CodeRabbit as sole SSOT over code/ADR/gates
  - Opening issues from CR text without agent PROVEN
  - Single CLI scope > ~300 files without split
  - Raising debt/quality budgets to silence CR
  - Empty form cycles
  - Admin merge bypass from audit prompt
  - Secrets/tokens in CR logs, issues, commits
  - Whole-repo code-level diagram dump
  - Mass layer moves without migration plan
tags: [audit, cycle, coderabbit, project, exhaustive, plan, implement, operator]
summary: Exhaustive cyclic project audit with CodeRabbit dual-pass — scope matrix, normalize, plan, fix, re-CR
max_body_lines: 260
---

# Exhaustive cyclic project audit with CodeRabbit

N-итерационный **исчерпывающий** аудит проекта BioETL: multi-domain scope
matrix → **CodeRabbit first** (CLI/App) → agent PROVEN re-check → normalize →
plan → issues → implement → PR CR re-pass → re-verify.

| Layer | Source |
| --- | --- |
| CR playbook | `docs/03-guides/coderabbit-audit-playbook.md` |
| CR dual-pass | `fragments/coderabbit-dual-pass.md` |
| Loop shell | `prompt.audit.orchestrator` |
| Domain packs | `prompt.audit.cyclic-pack` + architecture cycle |
| Config | `.coderabbit.yaml` (`profile: assertive`) |

**CodeRabbit is not SSOT.** Precedence: code/contracts → ADR/RULES →
architecture tests & quality gates → CR findings (must map to evidence).

Default **`N=10`**, **`MODE=full`**, **`CODERABBIT=required-then-agent`**,
**`CR_MODE=cli+app`**, **`INCLUDE_DOMAINS=all`**, **`MAX_FILES_PER_SCOPE=300`**,
все **`ALLOW_*=true`**.

Пустые циклы запрещены. Early-stop: 2 подряд итерации без новых actionable
PROVEN P0/P1, без CR/agent regression на fixed scopes, без падения scorecard
integral (если baseline загружен).

**УВЕЛИЧИВАТЬ бюджеты техдолга ЗАПРЕЩЕНО.**

## Params

| Param | Default |
| --- | --- |
| `N` | `10` |
| `SCOPE` | `all` (expand via domain matrix) or path CSV |
| `MODE` | `full` (`audit` \| `audit+plan` \| `audit+issues`) |
| `LANGUAGE` | `ru` |
| `AUDIT_MODE` | `full` \| `differential` |
| `CODERABBIT` | `required-then-agent` \| `agent-only` (explicit) |
| `CR_MODE` | `cli+app` \| `cli` \| `app` \| `pr-only` |
| `INCLUDE_DOMAINS` | `all` or CSV: see domain matrix |
| `MAX_FILES_PER_SCOPE` | `300` (hard CLI cap; split if exceeded) |
| `MAX_ISSUES_PER_ITERATION` | `5` |
| `MAX_WAVES_PER_ITERATION` | `3` |
| `ALLOW_ISSUE_WRITE` | `true` |
| `ALLOW_PUSH` | `true` |
| `ALLOW_MERGE` | `true` |
| `ALLOW_CLOSE` | `true` |
| `BASE_BRANCH` | `main` |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |
| `WORK_BRANCH` | `fix/coderabbit-project-cycle-<shortsha>` |

## Domain matrix (exhaustive when `INCLUDE_DOMAINS=all`)

Каждый domain — отдельный leaf-scope (или набор leaf scopes ≤ MAX_FILES).

| Domain id | Paths (indicative) | Domain method / focus |
| --- | --- | --- |
| `architecture` | `src/bioetl/**` layers, `.importlinter`, `tests/architecture/**` | `prompt.architecture.cycle` / 10-cat scorecard |
| `domain` | `src/bioetl/domain/**` | purity, ports, aggregates |
| `application` | `src/bioetl/application/**` (split core / services / composite) | hotspots, DI purity |
| `infrastructure` | `src/bioetl/infrastructure/**` | adapters, storage, HTTP |
| `composition` | `src/bioetl/composition/**` | DI-only, factories |
| `interfaces` | `src/bioetl/interfaces/**` | thin CLI/HTTP; no infra imports |
| `tests` | `tests/**`, quality test matrix | `prompt.audit.tests-cycle` |
| `docs` | `docs/00-project/**`, `docs/02-architecture/**` | `prompt.audit.docs-cycle` |
| `tech-debt` | scorecard, residual, inventories | `prompt.audit.tech-debt-cycle` |
| `repo-tree` | root, allowlist, clutter | `prompt.audit.repo-tree-cycle` |
| `gha` | `.github/workflows/**`, actions | `prompt.audit.github-actions` |
| `agents` | `.codex/**`, `.junie/**`, `.devin/**` | `prompt.audit.agents-runtime` |
| `diagrams` | `docs/02-architecture/diagrams/**` | `prompt.audit.diagrams` |
| `observability` | `grafana/**`, prom rules (if requested) | dashboard cycle (optional) |
| `configs` | `configs/**` | contracts, budgets no-growth |
| `scripts` | `scripts/**` | zero-import / temp governance |

`differential`: only paths changed vs `origin/BASE_BRANCH` ∩ matrix.

## CodeRabbit contract

### Preflight CR

1. `coderabbit --version` (or note App-only).
2. Auth: key from root `.env` (`CODERABBIT_API_KEY`) — **never** print token.
3. Config present: `.coderabbit.yaml`.
4. File-count each leaf: `git ls-files '<glob>' | wc -l` — split if ≥ MAX_FILES.
5. If CR unavailable and `CODERABBIT=required-then-agent` → write
   `coderabbit/DEGRADED.md`, **block mutations** (plan/read-only only).

### CLI invocation pattern (per leaf)

```bash
export AUDIT_TS=$(date -u +%Y%m%d_%H%M)
export OUT="reports/audit-runs/<run_id>/iteration-<i>/coderabbit/<scope_id>"
mkdir -p "$OUT"
coderabbit review --base=<BASE_BRANCH> --plain \
  | tee "$OUT/review_coderabbit_${scope_id}_${AUDIT_TS}.log"
```

For path focus beyond CLI base-diff: sparse worktree or staged scope only
(playbook). Rate-limit: sequential scopes + backoff.

### CR → finding mapping

Each CR claim becomes a candidate finding only after **agent PROVEN**:

| CR severity (approx) | priority |
| --- | --- |
| critical / security / layer break | P0 |
| major correctness / silent contract | P1 |
| maintainability / drift / missing tests | P2 |
| style / nit without risk | drop or P3 |

`method` must include `coderabbit` when sourced from CR. Drop pure style unless
it hides correctness. Skip themes already closed unless **regression proven**.

### BioETL review prompt (paste into CR / agent context)

```text
You are reviewing BioETL (hexagonal + DDD + medallion + local-only ADR-010).
- Domain stays I/O-free; DI only in composition.
- Evidence: path + symbol + broken invariant.
- Do not propose increasing quality/debt budgets.
- Docker/monitoring not required for local default.
- Ignore pure style nits unless they hide correctness risk.
Output: severity, path, claim, invariant, fix class, acceptance check.
```

## Preflight (agent)

1. `git status --porcelain`; SHA; branch; `gh auth status` (no tokens).
2. Dirty foreign work → worktree.
3. Freeze baseline: SHA, scorecard integral, debt gates, open architecture issues.
4. Expand `INCLUDE_DOMAINS` → leaf scope plan with file counts.
5. `run_id = <UTC>-cr-project-cycle-<shortsha>`
6. Artifacts: `reports/audit-runs/<run_id>/` (+ optional mirror
   `reports/audit/coderabbit-project/`).

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Scope freeze** | Leaf matrix for this iter (full or residual fixed scopes). Record file counts. |
| **B CodeRabbit** | Run CR per leaf (CLI and/or ensure PR App). Store under `iteration-i/coderabbit/<scope>/`. |
| **C Agent re-check** | Dual-pass: keep only PROVEN; add agent-only PROVEN if needed. |
| **D Cross-gates** | import-linter / architecture subset / debt gates / scorecard as available — CR cannot override green gates without evidence. |
| **E Normalize** | `findings.json` (finding-schema); domain tags; dedupe vs open GH issues. |
| **F Plan** | `plan.json` waves ≤ MAX_WAVES; P0→P1→lowest residual; debt ↓ or flat only. |
| **G Issues** | Create if ALLOW_ISSUE_WRITE + PROVEN; cap MAX_ISSUES; one issue per root-cause. |
| **H Implement** | WORK_BRANCH; minimal diffs; no drive-by; no budget raises. |
| **I PR + CR re-pass** | If ALLOW_PUSH: PR; wait CR App + required checks; agent disposition of residual CR. |
| **J Post** | resolved \| unchanged \| regressed \| new; re-CR fixed scopes; `delta.md`. |

`MODE=audit` → stop after E. `audit+plan` → after F. `full` → through J.

## Score / coverage (project health)

Each iteration record in `summary.md`:

| Signal | Source |
| --- | --- |
| architecture integral (if present) | `architecture-quality-scorecard.json` |
| debt gates pass/fail | `debt-governance-gates.json` |
| import-linter | `.importlinter` |
| CR scopes run / degraded | iteration coderabbit tree |
| PROVEN open P0–P3 counts | findings.json |
| surface_score 0–3 | audit-scale (cap if P0/P1 open) |

Optional: run architecture 10-category table when `architecture` ∈ domains
(`prompt.architecture.cycle` method).

## Focus checklist (each cycle)

- [ ] Scope file counts ≤ MAX_FILES_PER_SCOPE (or split documented)
- [ ] CR dual-pass order honored (or DEGRADED documented)
- [ ] No issue from CR-only unproven text
- [ ] Findings path-level PROVEN; secrets absent
- [ ] Debt budgets unchanged or reduced
- [ ] ADR-010 local-only not violated by "fix"
- [ ] Fixed scopes re-CR'd or explicitly deferred
- [ ] No empty form iteration

## Priority hints

- **P0**: authz/security, data-loss, wrong medallion write, secret leak path
- **P1**: forbidden layer import, silent contract break, non-deterministic critical write
- **P2**: coupling/hotspot, docs/ADR drift, maintainability with blast radius
- **P3**: local hygiene / style with residual risk only

## Outputs

```text
reports/audit-runs/<run_id>/
  run.json
  baseline.json
  scope-matrix.md
  iteration-<i>/
    coderabbit/<scope_id>/
    findings.json
    plan.json
    issues.jsonl
    summary.md
    delta.md
  final-summary.md
reports/audit/coderabbit-project/
  report.md
  findings.json
```

## Stop

- Empty/invalid SCOPE; CR required but DEGRADED without agent-only override
- P0 "fixed" by raising budgets
- Scope > cap without split
- Orchestrator hard-stop; secret leak risk
- Admin merge bypass via this prompt

## Success

- All planned domains covered at least once (or residual-only after iter 1 with justification)
- CR dual-pass artifacts + PROVEN findings under run dir
- Plan waves done or deferred with reason
- No new P0/P1 regression on fixed scopes after re-CR
- `final-summary.md` after N or early-stop

## Related

- Playbook: `docs/03-guides/coderabbit-audit-playbook.md`
- Dual-agent + CR: `prompt.audit.dual-agent-cycle`
- Domain pack: `prompt.audit.cyclic-pack`
- Architecture: `prompt.architecture.cycle`
- Closeout: `prompt.closeout.grok`
