---
id: prompt.audit.project.new2.security-secrets
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
  - ALLOW_ISSUE_WRITE
  - ALLOW_PUSH
  - ALLOW_MERGE
  - ALLOW_CLOSE
  - MAX_ISSUES_PER_ITERATION
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
related_ssot:
  - AGENTS.md
  - docs/00-project/NORMATIVE_SOURCES.md
  - docs/00-project/RULES.md
  - docs/01-requirements/REQUIREMENTS.md
  - docs/01-requirements/traceability/requirements-traceability-crosswalk.csv
  - .github/workflows
  - .github/dependabot.yml
  - docs/00-project/ai/prompts/library/audit/github-actions.md
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
anti_patterns:
  - Inventing REQ-* IDs not in REQUIREMENTS.md / the traceability CSV
  - Editing .env without explicit per-task approval
  - Pasting secret values into issues, logs, or reports
  - Hardcoded tokens in tracked files
  - Empty form cycles
  - Mutations without PROVEN + requirement_id
  - Raising debt budgets
tags: [audit, security, secrets, env, supply-chain, cycle, operator]
summary: Cyclic secrets/security audit — .env policy, leak scan, GHA overlap, ALLOW_* true, early-stop
max_body_lines: 220
---

# Cyclic secrets / security-adjacent audit

Env guardrail + leak hunt. Не полный GHA-цикл (см. new2.github-actions) и не
VCR cassettes (см. vcr-http). Loop: `prompt.audit.orchestrator`.
Library defaults: **`ALLOW_*=true`**. **Не печатать значения секретов.**

## Params

| Param | Default |
| --- | --- |
| `N` | `10` |
| `SCOPE` | `.github/ src/bioetl/ scripts/ configs/` |
| `MODE` | `full` (`audit` \| `audit+issues` \| `full`) |
| `LANGUAGE` | `ru` |
| `AUDIT_MODE` | `full` \| `differential` |
| `ALLOW_ISSUE_WRITE` | `true` |
| `ALLOW_PUSH` | `true` |
| `ALLOW_MERGE` | `true` |
| `ALLOW_CLOSE` | `true` |
| `MAX_ISSUES_PER_ITERATION` | `5` |
| `BASE_BRANCH` | `main` |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |
| `WORK_BRANCH` | `fix/security-cycle-new2-<shortsha>` |

## Anchors

- `.env` read-only unless operator approved a named task
- Named env indirection in YAML; no `${ENV_VAR}` interpolation in tracked provider YAML
- CI leak/OSV/secret-scan jobs vs docs — evidence without dumping secrets
- PROVEN finding MUST have `requirement_id`

## Preflight

1. `git status --porcelain`; SHA. Do not open `.env` in reports.
2. `run_id = <UTC>-sec-new2-<shortsha>`. Marker: `Cycle-run: <run_id>`.
3. Artifacts: `reports/audit-runs/<run_id>/` — redact.

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Policy** | Env/secret rules in AGENTS.md / RULES §5.4 vs practice. |
| **B Tracked leaks** | High-entropy / key-shaped strings in SCOPE (redact in findings). |
| **C CI overlap** | Secret scanning / OSV / Dependabot present and not disabled silently. |
| **D Issues** | ALLOW_ISSUE_WRITE + PROVEN + `requirement_id`. Title `[security][<REQ-id>][P#]`. No secret in body. |
| **E Fix** | Rotate instructions (operator), remove literals, pin scans. Never edit `.env` without approval. |
| **F Validate** | Re-scan touched paths. Close only on `origin/main` if ALLOW_CLOSE. |

## Early-stop

`new_issues_i == 0` **и** `open_cycle_issues == 0` → STOP.
Confirmed live secret in git → P0 + stop leak (do not repeat value).

## Success

- Leak findings without secret material in GitHub
- `.env` untouched unless explicitly approved
