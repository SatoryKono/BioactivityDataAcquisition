---
id: prompt.audit.github-actions
version: 1.2.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [any]
params: [SCOPE, MODE, LANGUAGE, AUDIT_MODE, REQUIRE_GH_TRACKING]
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
  - fragments/generic-nine-contract.md
related_ssot:
  - AGENTS.md
  - .github/workflows
  - docs/00-project/NORMATIVE_SOURCES.md
anti_patterns:
  - Optimizing CI cost before fixing trust boundaries
  - Broad write permissions “for convenience”
  - Treating untrusted PR code as safe under privileged triggers
tags: [audit, ci, github-actions, security, operator]
summary: GitHub Actions supply-chain and correctness audit
max_body_lines: 140
---

# GitHub Actions audit

**Kit:** prompt 5 of `prompt.audit.generic-nine.pack`.
Audit `.github/workflows` as executable supply chain and security boundary.
Order: **trust model** (events, tokens, secrets, third-party actions, runners)
→ correctness → reproducibility → performance/cache → artifacts → deploy.
Optimization is secondary to credential and release integrity.


**Machine outputs:** always pair `report.md` + `findings.json` under `reports/audit/gha/`. For multi-iteration loops use `prompt.audit.orchestrator` and `reports/audit-runs/<run_id>/`.

## Params

| Param | Default |
| --- | --- |
| `SCOPE` | `.github/workflows` |
| `MODE` | `audit` \| `propose-patches` |
| `LANGUAGE` | `ru` |
| `AUDIT_MODE` | `full` \| `differential` |
| `REQUIRE_GH_TRACKING` | `false` |

## Method

1. Inventory: workflow → triggers → filters → permissions → jobs → runner →
   environment → actions → cache → artifacts → secrets/OIDC → deploy.
2. Security: `pull_request_target` / `workflow_run` necessity; untrusted code
   in privileged context; minimal `permissions`; no secret echo; third-party
   actions pin (prefer full commit SHA); self-hosted isolation; OIDC over
   long-lived cloud keys when applicable.
3. Untrusted interpolation into shell: not auto-vuln — verify sink.
4. Correctness: timeouts, concurrency (careful with deploy
   `cancel-in-progress`), cache keys tied to lockfiles, recover on cache miss,
   artifact retention, matrix vs supported versions, reusable workflows.

## Checklist (sample)

- [ ] Default permissions least privilege
- [ ] Dangerous triggers justified
- [ ] Actions not on floating `main`/`latest` without pin policy exception
- [ ] Deploy uses environment protections where required

## Output

- `reports/audit/gha/report.md`
- `reports/audit/gha/findings.json` (finding-schema)
- optional extras listed below or in method notes
- `surface_score` 0–3 (map any 0–5 dimensions via audit-scale)
- findings per finding-schema; top remediations
- `MODE=propose-patches` / write modes: only after operator approval and ALLOW flags when orchestrated

## Stop

Live secret material in logs/artifacts → P0 stop. Do not disable security
gates to greenwash CI.
