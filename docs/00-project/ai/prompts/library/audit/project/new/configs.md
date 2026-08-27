---
id: prompt.audit.project.new.configs
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
  - docs/01-requirements/REQUIREMENTS.md
  - docs/01-requirements/traceability/requirements-traceability-crosswalk.csv
  - docs/00-project/RULES.md
  - configs/README.md
  - configs/_schema/pipeline.json
  - configs/quality/config_compatibility_registry.yaml
  - configs/quality/debt_scorecard.yaml
  - .codex/agents/py-config-bot.md
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
  - docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md
anti_patterns:
  - Inventing REQ-* IDs not in REQUIREMENTS.md / the traceability CSV
  - Weakening schema validation so invalid input passes
  - Reintroducing retired aliases as canonical fields
  - Putting secrets or ${ENV_VAR} interpolation in tracked provider YAML
  - Raising quality/debt budgets or exemptions
  - Editing .env without explicit per-task approval
  - Empty form cycles
  - ALLOW_* true by library default
tags: [audit, configs, schema, cycle, operator]
summary: Improved cyclic config audit — schema hierarchy, compatibility, fail-closed ALLOW, early-stop
max_body_lines: 230
---

# Improved cyclic project-config audit

Улучшает `prompt.audit.cycle.configs`. Role: `.codex/agents/py-config-bot.md`
(Junie peer). Loop: `prompt.audit.orchestrator`.

Library defaults: **`ALLOW_*=false`**. Пустые циклы запрещены.
**УВЕЛИЧИВАТЬ бюджеты техдолга ЗАПРЕЩЕНО.**

## Params

| Param | Default |
| --- | --- |
| `N` | `10` |
| `SCOPE` | `configs/ pyproject.toml mkdocs.yml .importlinter .coderabbit.yaml` |
| `MODE` | `full` (`audit` \| `audit+issues` \| `full`) |
| `LANGUAGE` | `ru` |
| `AUDIT_MODE` | `full` \| `differential` |
| `ALLOW_ISSUE_WRITE` | `false` |
| `ALLOW_PUSH` | `false` |
| `ALLOW_MERGE` | `false` |
| `ALLOW_CLOSE` | `false` |
| `MAX_ISSUES_PER_ITERATION` | `5` |
| `BASE_BRANCH` | `main` |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |
| `WORK_BRANCH` | `fix/configs-cycle-new-<shortsha>` |

## Hierarchy (do not invert)

1. `configs/base/*.yaml`
2. `configs/providers/{provider}.yaml`
3. `configs/entities/{provider}/{entity}.yaml`
4. `configs/composites/{name}.yaml`

Schemas: `configs/_schema/{pipeline,source,composite,dq}.json`.
Compatibility: `configs/quality/config_compatibility_registry.yaml`.
ADR-010: compose/Docker optional; do not require Redis for local default.

## Preflight

1. `git status --porcelain`; SHA. Чужой dirty → worktree.
2. Snapshot hashes of `configs/quality/**` budget files (read-only).
3. `run_id = <UTC>-configs-new-<shortsha>`. Marker: `Cycle-run: <run_id>`.
4. Artifacts: `reports/audit-runs/<run_id>/`.

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Inventory** | Tracked configs → schemas → tests → docs. Split tool configs vs pipeline YAML. |
| **B Schema** | Validate vs `_schema`. Retired aliases stay retired. Composite files keep `pipeline`, `schema`, `quality`, `filters`, `contracts`. |
| **C Secrets** | No secret literals / `${ENV_VAR}` in tracked provider YAML. Named indirection only. `.env` read-only. |
| **D Budgets** | Any increase vs snapshot → `REJECTED_POLICY`. |
| **E Issues/Fix** | ALLOW_ISSUE_WRITE + PROVEN + `requirement_id`. Title `[configs][<REQ-id>][P#]`. Smallest owner-file change. |
| **F Validate** | Focused config/schema tests. Debt effect `improved` \| `unchanged` \| `worsened`. Close only on `origin/main` if ALLOW_CLOSE. |

## Early-stop

`new_issues_i == 0` **и** `open_cycle_issues == 0` → STOP.
Два подряд цикла без новых PROVEN P0/P1 и без budget regression → STOP.

## Success

- Budget snapshot ↓ or flat
- Touched YAML has schema/test evidence
- `.env` untouched
