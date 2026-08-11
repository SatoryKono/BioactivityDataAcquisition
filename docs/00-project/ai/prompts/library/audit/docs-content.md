---
id: prompt.audit.docs-content
version: 1.1.0
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

## Output

- `reports/audit/docs-content/report.md`
- `reports/audit/docs-content/findings.json` (finding-schema)
- optional extras listed below or in method notes
- `surface_score` 0–3 (map any 0–5 dimensions via audit-scale)
- findings per finding-schema; top remediations
- `MODE=propose-patches` / write modes: only after operator approval and ALLOW flags when orchestrated

## Stop

Empty/invalid SCOPE → STOP. Secret in docs → P0 + stop leak. No actionable
PROVEN findings → `NO_ACTIONABLE_FINDINGS`.
