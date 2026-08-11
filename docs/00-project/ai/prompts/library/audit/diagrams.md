---
id: prompt.audit.diagrams
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
  - docs/02-architecture
anti_patterns:
  - Preferring pretty PNG over accurate text-as-code
  - Unpinned npx -y in production CI
  - Huge code-level diagrams of entire monorepo
tags: [audit, diagrams, mermaid, architecture, operator]
summary: Audit version-controlled diagrams and render scripts
max_body_lines: 140
---

# Diagrams audit

Audit architecture/technical diagrams as engineering artifacts: canonical
source, reproducible render, match to code/infra, and scripts/CI that build
them. A pretty but wrong diagram scores worse than a minimal accurate
text-as-code diagram.


**Machine outputs:** always pair `report.md` + `findings.json` under `reports/audit/diagrams/`. For multi-iteration loops use `prompt.audit.orchestrator` and `reports/audit-runs/<run_id>/`.

## Params

| Param | Default |
| --- | --- |
| `SCOPE` | docs diagrams + related scripts |
| `MODE` | `audit` \| `propose-patches` |
| `LANGUAGE` | `ru` |
| `AUDIT_MODE` | `full` \| `differential` |
| `REQUIRE_GH_TRACKING` | `false` |

## Method

1. Inventory: `.mmd`, PlantUML, Graphviz, drawio, embedded Mermaid in md/mdx,
   SVG/PNG under docs; scripts matching diagram/mermaid/c4.
2. Per diagram: source, generated output, renderer/version, owner, scope,
   last meaningful update, linked docs.
3. Classify: context, container, component, sequence/runtime, deployment,
   data, state, CI flow.
4. C4 as zoom levels (not religion); code-level only where complexity needs it.
5. Render smoke with **pinned** project tooling (avoid bare `npx -y` in CI).
6. Drift: if generated images tracked, clean workspace render +
   `git diff --exit-code` only when policy requires; else temp output.
7. No secrets/internal endpoints that must not be published.

## Output

- `reports/audit/diagrams/report.md`
- `reports/audit/diagrams/findings.json` (finding-schema)
- optional extras listed below or in method notes
- `surface_score` 0–3 (map any 0–5 dimensions via audit-scale)
- findings per finding-schema; top remediations
- `MODE=propose-patches` / write modes: only after operator approval and ALLOW flags when orchestrated

## Stop

Do not commit large binary churn without policy. Full-repo code diagram →
reject as out of method.
