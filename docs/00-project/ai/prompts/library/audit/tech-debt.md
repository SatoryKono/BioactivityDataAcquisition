---
id: prompt.audit.tech-debt
version: 1.3.0
status: active
class: operator-paste
owner: BioETL Team
runtimes:
- any
params:
- SCOPE
- MODE
- LANGUAGE
- AUDIT_MODE
- REQUIRE_GH_TRACKING
includes:
- fragments/git-safety.md
- fragments/debt-budget-ban.md
- fragments/env-guardrail.md
- fragments/evidence-contract-v3.md
- fragments/language-ru.md
- fragments/audit-scale.md
- fragments/finding-schema.md
- fragments/project-requirements-audit.md
related_ssot:
- AGENTS.md
- docs/00-project/RULES.md
- docs/00-project/governance/08-debt-ownership-playbook.md
- docs/00-project/NORMATIVE_SOURCES.md
anti_patterns:
- Raising debt/quality budgets or exemptions to “pass”
- Calling every style nit technical debt
- Priority by TODO count instead of blast radius
- Reporting raw marker counts as debt without false-positive triage
- Removing coverage exclusions to “pay down” without covering tests
- Retyping dynamic APIs without a runnable type checker to verify
tags:
- audit
- debt
- quality
- operator
summary: Evidence-based technical debt register with risk-ordered paydown
max_body_lines: 140
---
# Technical debt audit

Build an evidence-backed debt register bound to `_schema/finding-v3.schema.json`.
Never increase debt/quality budgets. Prioritize by probability × blast radius.

**Machine outputs:** `report.md` + `findings.json` under `reports/audit/tech-debt/`.
constraints, maintainability debt, obsolete deps, test debt, and architecture
drift. **Never increase** debt/quality budgets (see debt-budget-ban).
Prioritize by probability × blast radius, not TODO count.


**Machine outputs:** always pair `report.md` + `findings.json` under `reports/audit/tech-debt/`. For multi-iteration loops use `prompt.audit.orchestrator` and `reports/audit-runs/<run_id>/`.

## Params

| Param | Default |
| --- | --- |
| `SCOPE` | path cluster or theme |
| `MODE` | `audit` \| `propose-patches` |
| `LANGUAGE` | `ru` |
| `AUDIT_MODE` | `full` \| `differential` |
| `REQUIRE_GH_TRACKING` | `false` |

## Method

1. Collect markers in SCOPE: TODO/FIXME/HACK/XXX/WORKAROUND/TEMP/DEPRECATED,
   lint/type/test suppressions, compatibility shims, disabled checks, dead
   flags, oversized modules, cycles (use project tooling when available).
2. Triage false positives BEFORE counting: test-data patterns (`XXXXX`),
   guard-test infrastructure, docstrings/templates (`ADR-XXX`, `CVCL_XXXX`),
   tooling strings. Report measured debt, never raw hit counts.
3. For coverage-gated exclusions (`pragma: no cover`, `nosec`): check each
   line against `coverage.xml` (EXCLUDED vs executed). Never remove an
   exclusion without a covering test — removal alone lowers measured
   coverage and breaks gates.
4. For `type: ignore` at dynamic-API seams (decorators, `**kwargs: object`):
   prefer narrow `cast()`; do not retype without a runnable type checker
   to verify. Verify every remediation with the repo gate + unit tests.
5. For top items: history/blame age, owner, blast radius, tests protecting
   refactor, whether debt blocks security patch or feature.
3. Classify: code, tests, dependencies, architecture, data/schema, CI,
   observability, documentation, security, operational.
4. Read existing quality/debt budgets and registries; report **trend** without
   proposing higher limits.
5. Optional Sonar/analyzer metrics = signal only, not architecture substitute.

## Surface score (this domain)

| Score | Meaning |
| --- | --- |
| 3 | Debt identified with owner/risk/effort; new code does not worsen baseline |
| 2 | Main debt controlled; some items informal |
| 1 | Suppressions/workarounds without systemic management |
| 0 | Critical accumulated issues ignored or make change unsafe |

## Output

- `reports/audit/tech-debt/report.md` + `findings.json`
- kit extras: `technical-debt-register.csv` (id,path,line,type,evidence,age,risk,blast_radius,effort,owner,priority),
  `debt-heatmap.md`, top-20, quick wins vs strategic vs dependency debt
- `surface_score` 0–3; remediations; `MODE=propose-patches` only with approval
- Machine contract (`finding-v3`): `evidence` is ONE object
  `{path,line,command,scope,timestamp,exit_code,output}`; `fingerprint` is
  sha256 over `domain|requirement_id|root_cause|canonical_paths` (64 hex);
  `evidence_class` in `FACT|INFERENCE|GAP|CONTRADICTION`;
  `status` in `PROVEN|NOT_PROVEN` (closure tracked via `acceptance` text).
- Differential runs re-verify open items and rescan markers; close items
  through `acceptance`, never by deleting rows.

## Priority hints

- P0: security, data integrity, release correctness
- P1: high incident/feature-block probability
- P2: material cost-of-change
- P3: local cleanup

## Stop

Any remediation that **raises** a budget/exemption → reject. Propose only
debt-reducing or budget-neutral changes.
