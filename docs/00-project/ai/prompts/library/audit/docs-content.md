---
id: prompt.audit.docs-content
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
  - docs/00-project/NORMATIVE_SOURCES.md
  - docs/00-project/RULES.md
  - README.md
anti_patterns:
  - Counting Markdown files instead of verifying procedures
  - Inventing install/test commands not in manifests
  - Writing artifacts to repo root
  - Overlap dump of docs-pipeline findings (use prompt.audit.docs-pipeline)
tags: [audit, docs, content, operator]
summary: Evidence-based audit of project documentation content and drift
max_body_lines: 140
---

# Docs content audit

Audit documentation as the interface between code, developers, ops, and users.
Measure completeness, freshness, consistency, and **reproducibility** of
procedures — not file count. Re-check claims about commands, paths, config,
API, versions, and deploy against code/config.

**Kit:** prompt 1 of `prompt.audit.generic-nine.pack`.
**Disjoint scope:** content/IA/links/commands here. Generators, MkDocs build,
and publish pipeline → `prompt.audit.docs-pipeline`.


**Machine outputs:** always pair `report.md` + `findings.json` under `reports/audit/docs-content/`. For multi-iteration loops use `prompt.audit.orchestrator` and `reports/audit-runs/<run_id>/`.

## Params

| Param | Default |
| --- | --- |
| `SCOPE` | `README.md docs/` (narrow as needed) |
| `MODE` | `audit` \| `propose-patches` |
| `LANGUAGE` | `ru` |
| `AUDIT_MODE` | `full` \| `differential` |
| `REQUIRE_GH_TRACKING` | `false` |

## Method

1. Inventory under SCOPE: README*, docs/**, CONTRIBUTING*, SECURITY*, SUPPORT*,
   CHANGELOG*, LICENSE*, CODE_OF_CONDUCT*, ADR, API schemas, runbooks, diagrams
   indexes, onboarding, troubleshooting, release notes.
2. Per doc: audience, purpose, SoT, related module, owner (if any), last
   meaningful change, links, generated sections.
3. Map to Diátaxis: tutorial / how-to / reference / explanation (project style
   guide first; else Google/Microsoft developer style as orientation only).
4. Verify bootstrap/install/build/test/run/lint commands against manifests.
5. Resolve relative links; flag TODO/FIXME/TBD in operational/security docs
   without owner/issue.
6. Detect contradictory instructions across two docs.

## Checklist (sample)

- [ ] README states project purpose
- [ ] Bootstrap path confirmed from clean checkout notes
- [ ] Commands match manifests/CI
- [ ] Required env vars documented (no secret values)
- [ ] Links resolve; runtime versions vs CI
- [ ] API reference vs schema/code
- [ ] No dangerous/stale deploy/runbook steps

## Surface score (this domain)

| Score | Meaning |
| --- | --- |
| 3 | Critical user/eng scenarios described; commands checked; links/build gated |
| 2 | Main path correct; some stale or missing sections |
| 1 | Material docs↔code drift or mostly manual checks |
| 0 | Critical instructions missing, unreproducible, or dangerously wrong |

P0: compromise / data loss / destructive prod action. P1: wrong
bootstrap/deploy/security/recovery. P2: large gaps/drift. P3: editorial.

## Output

- `reports/audit/docs-content/report.md` + `findings.json`
- kit extras: `docs-inventory.csv`, `broken-links.json`, `stale-docs.csv`,
  `docs-code-drift.csv` (CSV min: path,type,audience,owner,last_change,status,score,priority,evidence)
- `surface_score` 0–3; remediations; `MODE=propose-patches` only with approval

## Stop

Empty/invalid SCOPE → STOP. Secret in docs → P0 + stop leak. No actionable
PROVEN findings → `NO_ACTIONABLE_FINDINGS`.
