---
id: prompt.audit.project.new.coderabbit
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
  - fragments/project-requirements-audit.md
  - fragments/unknown-params.md
  - fragments/reports-output.md
  - fragments/shell-portability.md
  - fragments/orchestrator-guards.md
  - fragments/coderabbit-dual-pass.md
  - fragments/peer-review-gate.md
related_ssot:
  - AGENTS.md
  - docs/00-project/NORMATIVE_SOURCES.md
  - docs/01-requirements/REQUIREMENTS.md
  - docs/01-requirements/traceability/requirements-traceability-crosswalk.csv
  - docs/03-guides/coderabbit-audit-playbook.md
  - docs/03-guides/development/coderabbit-local-reviews.md
  - .coderabbit.yaml
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
  - docs/00-project/ai/prompts/library/audit/project/new/README.md
  - reports/quality/architecture-quality-scorecard.json
  - reports/quality/debt-governance-gates.json
  - docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md
anti_patterns:
  - Inventing REQ-* IDs not in REQUIREMENTS.md / the traceability CSV
  - Treating CodeRabbit as SSOT over code/ADR/gates
  - Opening issues from CR text without agent PROVEN
  - Running CR before domains 1–9 of this new pack
  - Single CLI scope over ~300 files without a split
  - Raising debt/quality budgets to silence CR
  - Admin merge bypass from an audit prompt
  - Secrets/tokens in CR logs, issues, or commits
  - Empty form cycles
  - ALLOW_* true by library default
tags: [audit, cycle, coderabbit, project, exhaustive, operator]
summary: Improved cyclic project+CodeRabbit audit — dual-pass, peer gate, fail-closed ALLOW, early-stop
max_body_lines: 250
---

# Improved cyclic project audit with CodeRabbit

Улучшает `prompt.audit.cycle.coderabbit` +
`prompt.audit.coderabbit-project-cycle`. **CodeRabbit is not SSOT.**
Гони **после** `prompt.audit.project.new.docs` … `dashboards` (домены 1–9),
иначе CR-шум не отличить от известных P0/P1.

Library defaults: **`ALLOW_*=false`**,
**`CODERABBIT=required-then-agent`**. Пустые циклы запрещены.

## Params

| Param | Default |
| --- | --- |
| `N` | `10` |
| `SCOPE` | `all` or path CSV |
| `MODE` | `full` (`audit` \| `audit+plan` \| `audit+issues` \| `full`) |
| `LANGUAGE` | `ru` |
| `AUDIT_MODE` | `full` \| `differential` |
| `CODERABBIT` | `required-then-agent` |
| `CR_MODE` | `cli+app` |
| `INCLUDE_DOMAINS` | `all` |
| `MAX_FILES_PER_SCOPE` | `300` |
| `MAX_ISSUES_PER_ITERATION` | `5` |
| `MAX_WAVES_PER_ITERATION` | `3` |
| `ALLOW_ISSUE_WRITE` | `false` |
| `ALLOW_PUSH` | `false` |
| `ALLOW_MERGE` | `false` |
| `ALLOW_CLOSE` | `false` |
| `BASE_BRANCH` | `main` |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |
| `WORK_BRANCH` | `fix/cr-cycle-new-<shortsha>` |

## Domain matrix (`INCLUDE_DOMAINS=all`)

Use **this** pack’s cards: `prompt.audit.project.new.docs` … `dashboards`,
plus `prompt.audit.github-actions` and `prompt.audit.repo-tree-cycle`.
Split any leaf ≥ MAX_FILES_PER_SCOPE files.

## CodeRabbit contract

1. `coderabbit --version`. Auth from root `.env` — **never** print the token.
2. Config: `.coderabbit.yaml`. Split oversized leaves.
3. If CR unavailable and `CODERABBIT=required-then-agent` → `DEGRADED.md` and
   **block mutations**.
4. Each CR claim becomes a finding only after **agent PROVEN**.
   critical→P0, major→P1. `method` includes `coderabbit` when sourced from CR.
5. Peer-review gate before merge when two implement streams exist.

## Preflight

1. `git status --porcelain`; SHA; `gh auth status` (no tokens).
2. Freeze baseline: SHA, scorecard integral, debt gates.
3. `run_id = <UTC>-cr-new-<shortsha>`. Marker: `Cycle-run: <run_id>`.
4. Artifacts: `reports/audit-runs/<run_id>/`.

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Scope** | Leaf matrix + file counts. |
| **B CR** | Dual-pass fragment: CLI and/or App. Store logs under `iteration-<i>/coderabbit/`. |
| **C Agent** | Keep PROVEN only; add agent-only PROVEN if needed. Map to `requirement_id`. |
| **D Plan** | Waves ≤ MAX_WAVES. Debt ↓ or flat. |
| **E Issues** | ALLOW_ISSUE_WRITE + PROVEN. Title `[cr][<REQ-id>][P#]`. |
| **F Fix** | WORK_BRANCH. PR CR re-pass if ALLOW_PUSH. Close only on `origin/main` if ALLOW_CLOSE. |

## Early-stop

`new_issues_i == 0` **и** `open_cycle_issues == 0` → STOP.
Два подряд цикла без новых PROVEN P0/P1 after CR+agent и без gate regression → STOP.

## Success

- CR claims mapped to agent PROVEN + `requirement_id`
- No budget raise to silence CR; no token leakage
- Domains 1–9 already run or explicitly waived by operator
