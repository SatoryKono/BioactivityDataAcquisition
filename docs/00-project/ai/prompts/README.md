______________________________________________________________________

Version: 4.0.0
Status: active
Class: internal (repo-only entrypoint; excluded from MkDocs)
Owner: BioETL Team
Last verified: '2026-09-04'
Epic: '#10081'

______________________________________________________________________

# AI Prompts Surface — Prompt Library

Operator **paste templates**, shared **fragments**, and `REGISTRY.yaml`.
This directory is **not** governance or runtime SSOT.

## Authority

When a prompt conflicts with active sources, **active sources win**:

1. `.codex/**`, `.junie/**`, `.devin/**`
2. `AGENTS.md` → `docs/00-project/NORMATIVE_SOURCES.md` → `RULES.md` / ADRs
3. This library

## Layout

```text
docs/00-project/ai/prompts/
  README.md
  REGISTRY.yaml          # 15 scenarios + entries
  domains.yaml           # 24 ADR-060 overlays (consolidated)
  CATALOG.md             # optional, from python -m scripts.ai.prompts catalog
  _schema/*.json         # 6 schemas
  fragments/             # 12 reusable blocks
  library/{audit,plan,test,config,doc,closeout,session}/
  profiles/*.yaml        # audit-readonly | differential | full-write
```

Historical copies: `docs/99-archive/prompts-2026-09/`.

## 15 scenarios

See `REGISTRY.yaml` `scenarios:`. Primary cards:

| Scenario | Prompt id | Card |
| --- | --- | --- |
| session-bootstrap | `prompt.session.grok-bootstrap` | [library/session/bootstrap.md](library/session/bootstrap.md) |
| audit-cycle | `prompt.audit.cycle` | [library/audit/cycle.md](library/audit/cycle.md) |
| audit-tech-debt | `prompt.audit.tech-debt` | [library/audit/tech-debt.md](library/audit/tech-debt.md) |
| plan-scoped | `prompt.plan.scoped` | [library/plan/scoped.md](library/plan/scoped.md) |
| test-cycle | `prompt.tests.cycle` | [library/test/cycle.md](library/test/cycle.md) |
| test-fix-retest | `prompt.tests.fix-retest` | [library/test/fix-retest.md](library/test/fix-retest.md) |
| config-validate | `prompt.config.validate` | [library/config/validate.md](library/config/validate.md) |
| doc-audit | `prompt.docs.audit` | [library/doc/audit.md](library/doc/audit.md) |
| debug-isolate | `prompt.debug.isolate` | [library/audit/debug.md](library/audit/debug.md) |
| closeout | `prompt.closeout.grok` | [library/closeout/grok-closeout.md](library/closeout/grok-closeout.md) |
| github-actions | `prompt.audit.github-actions` | [library/audit/github-actions.md](library/audit/github-actions.md) |
| agents-runtime | `prompt.audit.agents-runtime` | [library/audit/agents-runtime.md](library/audit/agents-runtime.md) |
| architecture-cycle | `prompt.architecture.cycle` | [library/audit/architecture.md](library/audit/architecture.md) |
| dashboard-audit | `prompt.observability.dashboard-audit-cycle` | [library/audit/dashboard.md](library/audit/dashboard.md) |
| sequential-run | `prompt.audit.sequential-run` | [library/audit/sequential-run.md](library/audit/sequential-run.md) |

Deprecated: `prompt.audit.grok-cycle`, `prompt.audit.cyclic-pack` → `prompt.audit.cycle`.

## Fragments

Twelve blocks under `fragments/`. Cards declare them in `includes:`.
Renderer also expands `{{> fragment-name}}` (example: `{{> debt-budget-ban}}`).

## Compile (ADR-060)

```text
python -m scripts.ai.prompts compile --domain docs --profile audit-readonly
python -m scripts.ai.prompts render prompt.audit.cycle --param SCOPE=src/bioetl --param DOMAIN=docs
python -m scripts.ai.prompts check
```

Overlays live in `domains.yaml` (not `overlays/*.yaml`). Generated markdown is
on-demand, not tracked.
