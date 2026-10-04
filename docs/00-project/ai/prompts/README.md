______________________________________________________________________

Version: 4.1.0
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

## Versioning

`Version:` in this file tracks the doc surface; `REGISTRY.yaml version:`
tracks the registry format; `domains.yaml version:` tracks the overlay pack.
The three are independent — never require them equal. `check` enforces
scenario-table content parity (`check_readme_scenarios`), not version equality.

## Layout

```text
docs/00-project/ai/prompts/
  README.md
  REGISTRY.yaml          # 18 scenarios + entries
  domains.yaml           # 28 ADR-060 overlays (consolidated)
  CATALOG.md             # optional, from python -m scripts.ai.prompts catalog
  _schema/*.json         # 6 schemas
  fragments/             # 14 reusable blocks
  library/{audit,plan,test,config,doc,closeout,session}/
  profiles/*.yaml        # audit-readonly | differential | full-write
```

Historical copies: `docs/99-archive/prompts-2026-09/`.

## 18 scenarios

See `REGISTRY.yaml` `scenarios:`. Primary cards (this table must mirror
`scenarios:` id + prompt id both ways — enforced by `check`):

| Scenario | Prompt id | Card |
| --- | --- | --- |
| session-bootstrap | `prompt.session.grok-bootstrap` | [library/session/bootstrap.md](library/session/bootstrap.md) |
| audit-cycle | `prompt.audit.cycle` | [library/audit/cycle.md](library/audit/cycle.md) |
| comprehensive-audit | `prompt.audit.comprehensive` | [library/audit/comprehensive.md](library/audit/comprehensive.md) |
| audit-tech-debt | `prompt.audit.tech-debt` | [library/audit/tech-debt.md](library/audit/tech-debt.md) |
| plan-scoped | `prompt.plan.scoped` | [library/plan/scoped.md](library/plan/scoped.md) |
| agent-efficiency | `prompt.plan.agent-efficiency` | [library/plan/agent-efficiency.md](library/plan/agent-efficiency.md) |
| test-cycle | `prompt.tests.cycle` | [library/test/cycle.md](library/test/cycle.md) |
| test-fix-retest | `prompt.tests.fix-retest` | [library/test/fix-retest.md](library/test/fix-retest.md) |
| config-validate | `prompt.config.validate` | [library/config/validate.md](library/config/validate.md) |
| doc-audit | `prompt.docs.audit` | [library/doc/audit.md](library/doc/audit.md) |
| debug-isolate | `prompt.debug.isolate` | [library/audit/debug.md](library/audit/debug.md) |
| closeout | `prompt.closeout.grok` | [library/closeout/grok-closeout.md](library/closeout/grok-closeout.md) |
| github-actions | `prompt.audit.github-actions` | [library/audit/github-actions.md](library/audit/github-actions.md) |
| agents-runtime | `prompt.audit.agents-runtime` | [library/audit/agents-runtime.md](library/audit/agents-runtime.md) |
| test-loop | `prompt.tests.loop` | [library/test/loop.md](library/test/loop.md) |
| architecture-cycle | `prompt.architecture.cycle` | [library/audit/architecture.md](library/audit/architecture.md) |
| dashboard-audit | `prompt.observability.dashboard-audit-cycle` | [library/audit/dashboard.md](library/audit/dashboard.md) |
| sequential-run | `prompt.audit.sequential-run` | [library/audit/sequential-run.md](library/audit/sequential-run.md) |

Deprecated: `prompt.audit.grok-cycle`, `prompt.audit.cyclic-pack` → `prompt.audit.cycle`.


## Comprehensive BioETL audit v2

`prompt.audit.comprehensive` integrates the audited P00-P20 package into the
current library rather than tracking a second monolithic prompt SSOT.

- P00 is the dependency-aware campaign/orchestrator.
- P01-P19 reuse existing domain overlays and shared fragments.
- Four dedicated overlays were added where the library had no clear PRIMARY
  owner: `composite-workflow`, `reproducibility`, `performance`,
  `repo-hygiene`.
- P20 is `prompt.audit.reconcile`, an independent read-only reconciliation
  card.
- POST-A/POST-B map to the existing fail-closed
  `prompt.audit.orchestrator`/closeout flow; raw P01-P19 findings must not
  create Issues before P20 reconciliation.

Typical entry:

```text
python -m scripts.ai.prompts render prompt.audit.comprehensive --param SCOPE=repo
```

Domain cards remain compilable independently with `audit-readonly`; the
comprehensive card owns ordering, shared evidence, handoffs and final
reconciliation.

## Fragments

Fourteen blocks under `fragments/`. Cards declare them in `includes:` — the
single SSOT prepend mechanism (`render` inlines them before the body).

Do **not** use inline `{{> fragment-name}}` tokens in operator-paste bodies:
`check` errors when a token duplicates an `includes:` entry
(`fragment_double_include`) and warns on any other inline token
(`fragment_inline_include`). Rendered paste budget (body + fragments) is
enforced separately from `max_body_lines` — see `DEFAULT_RENDERED_MAX_LINES`
in `scripts/ai/prompts/check.py` (per-card override `max_rendered_lines`).

## Compile (ADR-060)

```text
python -m scripts.ai.prompts compile --domain docs --profile audit-readonly
python -m scripts.ai.prompts render prompt.audit.cycle --param SCOPE=src/bioetl --param DOMAIN=docs
python -m scripts.ai.prompts check
```

Overlays live in `domains.yaml` (not `overlays/*.yaml`). Generated markdown is
on-demand, not tracked.

## Related Generators

- Grok project-domain audit workflow: scripts/ai/generate_project_domain_audit_workflow.py -- generates .grok/workflows/project-domain-audit.rhai
