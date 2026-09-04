---
id: prompt.audit.diagrams
version: 1.2.0
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
related_ssot:
- AGENTS.md
- docs/00-project/NORMATIVE_SOURCES.md
- docs/02-architecture
anti_patterns:
- Preferring pretty PNG over accurate text-as-code
- Unpinned npx -y in production CI
- Huge code-level diagrams of entire monorepo
tags:
- audit
- diagrams
- mermaid
- architecture
- operator
summary: Audit version-controlled diagrams and render scripts
max_body_lines: 140
---
# Diagrams audit

**Kit:** prompt 7 of `prompt.audit.generic-nine.pack`.
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

## Surface score (this domain)

| Score | Meaning |
| --- | --- |
| 3 | Text source in VCS; deterministic render; CI validation; model matches system |
| 2 | Diagrams current; some regeneration/review still manual |
| 1 | Binary-only, unclear source, or regular drift |
| 0 | Key diagram wrong enough to cause a bad security/deploy decision |

P0: wrong security/deploy model with ops impact. P1: wrong key dependency.
P2: stale runtime/component views. P3: layout/style.

## Output

- `reports/audit/diagrams/report.md` + `findings.json`
- kit extras: `diagram-inventory.csv`, `render-failures.txt`,
  `diagram-code-drift.csv`, canonical-source map
- `surface_score` 0–3; remediations; `MODE=propose-patches` only with approval

## Stop

Do not commit large binary churn without policy. Full-repo code diagram →
reject as out of method.
