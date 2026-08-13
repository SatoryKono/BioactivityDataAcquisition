---
id: prompt.audit.docs-pipeline
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
  - mkdocs.yml
anti_patterns:
  - Duplicating docs-content IA findings here
  - Treating generator exit 0 as semantic correctness
  - Publishing with hidden local-only state
tags: [audit, docs, pipeline, scripts, operator]
summary: Audit docs generate/validate/publish scripts and pipelines
max_body_lines: 140
---

# Docs pipeline audit

**Kit:** prompt 8 of `prompt.audit.generic-nine.pack`.
Audit scripts and pipelines that **generate, check, build, sync, or publish**
documentation. Prove chain: source-of-truth → generator → validation →
artifact → publication. Generated docs are not correct merely because the
generator exited 0.

**Disjoint scope:** pipeline/tooling here. Narrative content, Diátaxis IA,
stale prose → `prompt.audit.docs-content`.


**Machine outputs:** always pair `report.md` + `findings.json` under `reports/audit/docs-pipeline/`. For multi-iteration loops use `prompt.audit.orchestrator` and `reports/audit-runs/<run_id>/`.

## Params

| Param | Default |
| --- | --- |
| `SCOPE` | docs tooling (mkdocs, scripts, CI docs jobs) |
| `MODE` | `audit` \| `propose-patches` |
| `LANGUAGE` | `ru` |
| `AUDIT_MODE` | `full` \| `differential` |
| `REQUIRE_GH_TRACKING` | `false` |

## Method

1. Discover scripts/workflows: docgen, mkdocs/sphinx, openapi, linkcheck.
2. Pipeline map per step: entrypoint, package/version, inputs/outputs, env,
   network, cache, failure semantics, local vs CI caller.
3. If generated files are tracked: is SoT schema/code or generated Markdown?
4. Clean checkout: one-command docs build/check; pinned toolchain;
   deterministic output (no random timestamps in tracked artifacts).
5. Semantic checks: API reference vs public API; examples compile/test if
   claimed; internal link check; secrets not in generated pages/logs.
6. PR preview / publish path without hidden developer-local state.

## Surface score (this domain)

| Score | Meaning |
| --- | --- |
| 3 | One-command clean build; pinned toolchain; deterministic; links/API in CI |
| 2 | Pipeline reproducible; some semantic checks still manual |
| 1 | Hidden preconditions, generated drift, or unpredictable publish |
| 0 | Build broken, leaks secrets, or publishes dangerously wrong material |

P0: secret leak or wrong prod/security procedure. P1: stale API published as
current. P2: nondeterministic build/broken links. P3: style.

## Output

- `reports/audit/docs-pipeline/report.md` + `findings.json`
- kit extras: `docs-pipeline.csv`, `generated-files.csv`, `docs-build.log`,
  `link-report.json`, `source-of-truth-map.md`
- `surface_score` 0–3; remediations; `MODE=propose-patches` only with approval

## Stop

Do not publish or push docs from audit mode. Secret in generated output → P0.
