---
id: prompt.audit.cycle.configs
version: 1.1.0
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
anti_patterns:
  - Inventing REQ-* IDs not in REQUIREMENTS.md / the traceability CSV
  - Weakening schema validation so invalid input passes
  - Reintroducing retired aliases as canonical fields
  - Putting secrets or ${ENV_VAR} interpolation in tracked provider YAML
  - Raising quality/debt budgets or exemptions
  - Editing .env without explicit per-task approval
  - Empty form cycles
tags: [audit, configs, schema, cycle, operator]
summary: Cyclic audit of project config files, schemas, and compatibility
max_body_lines: 250
---

# Cyclic project-config audit

N-итерационный аудит **конфиг-файлов проекта**: иерархия, JSON-схемы,
compatibility, отсутствие секретов в tracked YAML, non-growth бюджетов.

Role surface: `.codex/agents/py-config-bot.md` (and Junie peer).
Loop shell: `prompt.audit.orchestrator`. Default **`N=10`**, **`MODE=full`**,
все **`ALLOW_*=true`**. Пустые циклы запрещены.

**УВЕЛИЧИВАТЬ бюджеты техдолга ЗАПРЕЩЕНО.**

## Params

| Param | Default |
| --- | --- |
| `N` | `10` |
| `SCOPE` | `configs/ pyproject.toml mkdocs.yml .importlinter commitlint.config.mjs package.json docker-compose.yml Dockerfile.bioetl .coderabbit.yaml` |
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

## Canonical hierarchy (do not invert)

1. `configs/base/*.yaml`
2. `configs/providers/{provider}.yaml`
3. `configs/entities/{provider}/{entity}.yaml`
4. `configs/composites/{name}.yaml`

Schemas: `configs/_schema/{pipeline,source,composite,dq}.json`.
Compatibility: `configs/quality/config_compatibility_registry.yaml`.
Settings precedence: explicit init/CLI > process ENV > repository-root `.env`
> typed defaults. CWD `config.yaml` is not a runtime Settings source.

## BioETL anchors

- Requirements: `docs/01-requirements/REQUIREMENTS.md` + traceability CSV; PROVEN findings need `requirement_id`
- Policy: `configs/README.md`
- Quality / debt: `configs/quality/debt_scorecard.yaml` (read-only budgets)
- Compose / Docker are **optional** (ADR-010). Do not require Redis or
  external orchestration for the local default.
- Tracked provider YAML must not contain `${ENV_VAR}` strings. Secrets use
  named indirection (`api_key_env: BIOETL_…`).
- Windows: `.\.venv-win\Scripts\python.exe`

## Preflight

1. `git status --porcelain`; SHA; branch. Foreign dirty work → worktree.
2. Confirm SCOPE paths exist; empty SCOPE → STOP.
3. Snapshot current debt/quality budget files (hashes only).
4. `run_id = <UTC>-configs-cycle-<shortsha>`
5. Artifacts: `reports/audit-runs/<run_id>/` + mirror `reports/audit/configs/`.

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Inventory** | Map tracked configs → schemas → generators → tests → docs. Separate tool configs (`pyproject.toml`, `.importlinter`, `.coderabbit.yaml`, compose) from pipeline/entity YAML. |
| **B Schema / compatibility** | Validate against `configs/_schema`. Confirm retired aliases stay retired (`source.batch_size`, source `health_check`/`retry`, `merge.column_groups_file`, etc.). Composite entity files still carry `pipeline`, `schema`, `quality`, `filters`, `contracts`. |
| **C Secrets / env** | No secret values and no `${ENV_VAR}` in tracked provider YAML. `.env` is read-only; do not create/edit/delete it. Document env **names** only. |
| **D Budgets / quality** | Compare `configs/quality/**` thresholds, exemptions, hotspot caps to the preflight snapshot. Any increase → `REJECTED_POLICY`. |
| **E Issues / Fix** | Create if ALLOW_ISSUE_WRITE + PROVEN + `requirement_id`. Title `[configs][<REQ-id>][P#]`. Smallest schema-valid owner-file change. Canonical generator only. |
| **F Validate** | Focused config/schema tests. Re-check touched schemas. Delta: resolved / unchanged / regressed / new. Record debt effect `improved` \| `unchanged` \| `worsened`. |

## Focus checklist (each cycle)

- [ ] Hierarchy base → provider → entity → composite not inverted
- [ ] Schema validation still rejects retired aliases
- [ ] No `${ENV_VAR}` / secret literals in tracked YAML
- [ ] `.env` untouched
- [ ] Debt/quality budgets flat or down
- [ ] Composite join keys are stable identifiers (never title)
- [ ] ADR-010: no new mandatory Docker/Redis for local default
- [ ] Generated artifacts refreshed only via canonical generator

## Stop

Weaken validation so invalid input passes → P0. Edit `.env` without explicit
operator approval → STOP. Raise a budget/exemption/threshold → reject.
Empty SCOPE → STOP.

## Success

- `findings.json` + `report.md` under `reports/audit-runs/<run_id>/`
- Budget snapshot delta is ↓ or flat
- Touched configs have schema/test evidence
- `surface_score` 0–3; cap at 1 if any P0 remains

## Related

- Role: `.codex/agents/py-config-bot.md`
- Adjacent: `prompt.audit.cycle.tech-debt`, `prompt.audit.cycle.architecture`
- Closeout: `prompt.closeout.grok`
- Previous: `prompt.audit.cycle.agents-memory` · Next: `prompt.audit.cycle.tests`
