---
id: prompt.audit.cycle.coderabbit
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
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
  - docs/00-project/ai/prompts/library/audit/cycle/README.md
  - reports/quality/architecture-quality-scorecard.json
  - reports/quality/debt-governance-gates.json
  - docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md
anti_patterns:
  - Treating CodeRabbit as SSOT over code/ADR/gates
  - Opening issues from CR text without agent PROVEN
  - Single CLI scope over ~300 files without a split
  - Raising debt/quality budgets to silence CR
  - Admin merge bypass from an audit prompt
  - Secrets/tokens in CR logs, issues, or commits
  - Empty form cycles
tags: [audit, cycle, coderabbit, project, exhaustive, operator]
summary: Exhaustive cyclic project audit with CodeRabbit dual-pass
max_body_lines: 280
---

# Cyclic full-project audit with CodeRabbit

N-итерационный **полный** аудит проекта: domain matrix → **CodeRabbit first** →
agent PROVEN → plan → issues → implement → PR CR re-pass → re-verify.

Замыкает пак `prompt.audit.cycle.*`. Гони **после** доменов 1–9, иначе CR-шум
не отличить от уже известных P0/P1.

| Layer | Source |
| --- | --- |
| CR playbook | `docs/03-guides/coderabbit-audit-playbook.md` |
| Dual-pass | `fragments/coderabbit-dual-pass.md` |
| Loop shell | `prompt.audit.orchestrator` |
| Config | `.coderabbit.yaml` |

**CodeRabbit is not SSOT.** Precedence: code/contracts → ADR/RULES →
architecture tests & quality gates → CR findings (must map to evidence).

Library defaults: **`N=10`**, **`MODE=full`**,
**`CODERABBIT=required-then-agent`**, **`CR_MODE=cli+app`**,
**`INCLUDE_DOMAINS=all`**, **`MAX_FILES_PER_SCOPE=300`**,
все **`ALLOW_*=false`** (fail-closed). Operator full-run must set ALLOW_*
explicitly. **УВЕЛИЧИВАТЬ бюджеты техдолга ЗАПРЕЩЕНО.**

## Params

| Param | Default |
| --- | --- |
| `N` | `10` |
| `SCOPE` | `all` (expand via domain matrix) or path CSV |
| `MODE` | `full` (`audit` \| `audit+plan` \| `audit+issues` \| `full`) |
| `LANGUAGE` | `ru` |
| `AUDIT_MODE` | `full` \| `differential` |
| `CODERABBIT` | `required-then-agent` |
| `CR_MODE` | `cli+app` (`cli` \| `app` \| `pr-only`) |
| `INCLUDE_DOMAINS` | `all` |
| `MAX_FILES_PER_SCOPE` | `300` |
| `MAX_ISSUES_PER_ITERATION` | `5` |
| `MAX_WAVES_PER_ITERATION` | `3` |
| `ALLOW_ISSUE_WRITE` | `false` (full-run: `true`) |
| `ALLOW_PUSH` | `false` (full-run: `true`) |
| `ALLOW_MERGE` | `false` (full-run: `true`) |
| `ALLOW_CLOSE` | `false` (full-run: `true`) |
| `BASE_BRANCH` | `main` |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |
| `WORK_BRANCH` | `fix/coderabbit-project-cycle-<shortsha>` |

## Domain matrix (`INCLUDE_DOMAINS=all`)

| Domain id | Paths (indicative) | Cycle method |
| --- | --- | --- |
| `docs` | `docs/`, `scripts/docs/` | `prompt.audit.cycle.docs` |
| `diagrams` | `docs/02-architecture/diagrams/`, `scripts/diagrams/` | `prompt.audit.cycle.diagrams` |
| `agents` | `.codex/`, `.junie/`, `src/memory/` | `prompt.audit.cycle.agents-memory` |
| `configs` | `configs/` | `prompt.audit.cycle.configs` |
| `tests` | `tests/`, quality matrix | `prompt.audit.cycle.tests` |
| `tech-debt` | scorecard, residual | `prompt.audit.cycle.tech-debt` |
| `architecture` | `src/bioetl/`, `.importlinter` | `prompt.audit.cycle.architecture` |
| `telemetry` | metrics, prom rules | `prompt.audit.cycle.telemetry` |
| `dashboards` | `grafana/dashboards/` | `prompt.audit.cycle.dashboards` |
| `gha` | `.github/workflows/` | `prompt.audit.github-actions` |
| `repo-tree` | root allowlist | `prompt.audit.repo-tree-cycle` |

Split any leaf with ≥ MAX_FILES_PER_SCOPE files.

## CodeRabbit contract

1. `coderabbit --version` (or note App-only). Auth from root `.env`
   (`CODERABBIT_API_KEY`) — **never** print the token.
2. Config: `.coderabbit.yaml`. File-count each leaf; split if over cap.
3. If CR unavailable and `CODERABBIT=required-then-agent` → write
   `iteration-<i>/coderabbit/DEGRADED.md` and **block mutations**.
4. CLI: `coderabbit review --base=<BASE_BRANCH> --plain` with `pipefail`;
   store logs under `iteration-<i>/coderabbit/<scope_id>/`.
5. Each CR claim becomes a finding only after **agent PROVEN**.
   critical→P0, major→P1, maintainability→P2, pure style→drop or P3.
6. `method` must include `coderabbit` when sourced from CR.

## Preflight

1. `git status --porcelain`; SHA; branch; `gh auth status` (no tokens).
2. Dirty foreign work → worktree.
3. Freeze baseline: SHA, scorecard integral, debt gates.
4. Expand `INCLUDE_DOMAINS` → leaf plan with file counts.
5. `run_id = <UTC>-cr-project-cycle-<shortsha>`
6. Artifacts: `reports/audit-runs/<run_id>/` +
   `reports/audit/coderabbit-project/`.

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Scope freeze** | Leaf matrix for this iter. Record file counts. |
| **B CodeRabbit** | Run CR per leaf (CLI and/or PR App). Store logs. |
| **C Agent re-check** | Dual-pass: keep only PROVEN; add agent-only PROVEN if needed. |
| **D Cross-gates** | import-linter / architecture subset / debt gates. CR cannot override a green gate without evidence. |
| **E Normalize** | `findings.json`; domain tags; dedupe vs open GH issues. |
| **F Plan** | `plan.json` waves ≤ MAX_WAVES; P0→P1; debt ↓ or flat only. |
| **G Issues** | Create if ALLOW_ISSUE_WRITE + PROVEN. One issue per root-cause. |
| **H Implement** | WORK_BRANCH; minimal diffs; no drive-by; no budget raises. |
| **I PR + CR re-pass** | If ALLOW_PUSH: PR; wait CR App + required checks; agent disposition of residual CR. |
| **J Post** | resolved \| unchanged \| regressed \| new; re-CR fixed scopes. |

`MODE=audit` stops after E. `audit+plan` after F. `full` through J.

## Focus checklist (each cycle)

- [ ] Scope file counts ≤ MAX_FILES_PER_SCOPE (or split documented)
- [ ] CR dual-pass order honored (or DEGRADED documented)
- [ ] No issue from CR-only unproven text
- [ ] Findings path-level PROVEN; secrets absent
- [ ] Debt budgets unchanged or reduced
- [ ] ADR-010 local-only not violated by a “fix”
- [ ] Fixed scopes re-CR'd or explicitly deferred
- [ ] No empty form iteration

## Stop

Empty/invalid SCOPE. CR required but DEGRADED without an explicit agent-only
override. P0 “fixed” by raising budgets. Scope over cap without a split.
Secret leak risk. Admin merge bypass via this prompt.

## Success

- Planned domains covered at least once (or residual-only after iter 1)
- CR dual-pass artifacts + PROVEN findings under the run dir
- Plan waves done or deferred with reason
- No new P0/P1 regression on fixed scopes after re-CR
- `final-summary.md` after N or early-stop

## Related

- Playbook: `docs/03-guides/coderabbit-audit-playbook.md`
- Dual-agent: `prompt.audit.dual-agent-cycle`
- Pack index: `docs/00-project/ai/prompts/library/audit/cycle/README.md`
- Closeout: `prompt.closeout.grok`
- Previous: `prompt.audit.cycle.dashboards`
