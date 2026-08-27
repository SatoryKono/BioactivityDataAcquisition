______________________________________________________________________

Version: 1.0.0
Status: active
Class: internal (repo-only index; not a paste card)
Owner: BioETL Team
Last verified: '2026-08-18'

______________________________________________________________________

# Full project-audit paste texts

Rendered **full** operator pastes (guardrail fragments inlined) for the
BioETL project audit suite: tech-debt, tests, docs, diagrams, configs,
architecture, agents, telemetry, dashboards, CodeRabbit.

Not runtime SSOT. Source cards remain `prompt.audit.cycle.*` and
`prompt.audit.<domain>`. Do not edit `full/*.md` by hand.

## How to paste

1. Router: `prompt.audit.project.pack`
2. Sequential run: `full/audit-sequential-run.md` or render
   `prompt.audit.sequential-run`
3. One domain: the matching `full/audit-cycle-*.md` file

Regenerate:

```powershell
.\.venv-win\Scripts\python.exe -m scripts.ai.prompts render prompt.audit.cycle.docs `
  --param N=10 --param MODE=full --param LANGUAGE=ru
.\.venv-win\Scripts\python.exe -m scripts.ai.prompts project-full-links --sync
```

The link-sync step rebases source-card-relative links for the deeper
`project/full/` output directory. `python -m scripts.ai.prompts check` fails if
that generated-link step was skipped.

## Files (`full/`)

| Source id | File |
| --- | --- |
| `prompt.audit.cyclic-pack` | [full/audit-cyclic-pack.md](full/audit-cyclic-pack.md) |
| `prompt.audit.sequential-run` | [full/audit-sequential-run.md](full/audit-sequential-run.md) |
| `prompt.audit.grok-cycle` | [full/audit-grok-cycle.md](full/audit-grok-cycle.md) |
| `prompt.audit.orchestrator` | [full/audit-orchestrator.md](full/audit-orchestrator.md) |
| `prompt.audit.cycle.docs` | [full/audit-cycle-docs.md](full/audit-cycle-docs.md) |
| `prompt.audit.cycle.diagrams` | [full/audit-cycle-diagrams.md](full/audit-cycle-diagrams.md) |
| `prompt.audit.cycle.agents-memory` | [full/audit-cycle-agents-memory.md](full/audit-cycle-agents-memory.md) |
| `prompt.audit.cycle.configs` | [full/audit-cycle-configs.md](full/audit-cycle-configs.md) |
| `prompt.audit.cycle.tests` | [full/audit-cycle-tests.md](full/audit-cycle-tests.md) |
| `prompt.audit.cycle.tech-debt` | [full/audit-cycle-tech-debt.md](full/audit-cycle-tech-debt.md) |
| `prompt.audit.cycle.architecture` | [full/audit-cycle-architecture.md](full/audit-cycle-architecture.md) |
| `prompt.audit.cycle.telemetry` | [full/audit-cycle-telemetry.md](full/audit-cycle-telemetry.md) |
| `prompt.audit.cycle.dashboards` | [full/audit-cycle-dashboards.md](full/audit-cycle-dashboards.md) |
| `prompt.audit.cycle.coderabbit` | [full/audit-cycle-coderabbit.md](full/audit-cycle-coderabbit.md) |
| `prompt.audit.docs-content` | [full/audit-docs-content.md](full/audit-docs-content.md) |
| `prompt.audit.docs-pipeline` | [full/audit-docs-pipeline.md](full/audit-docs-pipeline.md) |
| `prompt.audit.diagrams` | [full/audit-diagrams.md](full/audit-diagrams.md) |
| `prompt.audit.tests-system` | [full/audit-tests-system.md](full/audit-tests-system.md) |
| `prompt.audit.tech-debt` | [full/audit-tech-debt.md](full/audit-tech-debt.md) |
| `prompt.audit.repo-tree` | [full/audit-repo-tree.md](full/audit-repo-tree.md) |
| `prompt.audit.github-actions` | [full/audit-github-actions.md](full/audit-github-actions.md) |
| `prompt.audit.agents-runtime` | [full/audit-agents-runtime.md](full/audit-agents-runtime.md) |
| `prompt.architecture.cycle` | [full/architecture-cycle.md](full/architecture-cycle.md) |

## Improved source cards (`new/`)

Improved rewrite of the 10 cycle domains (`prompt.audit.project.new.*`)
with library-default `ALLOW_*=true`.
These are **source cards** (edit here). They do **not** replace `cycle/` as
pack SSOT until an operator adopts them. Do not mix with generated `full/`.

Index: [new/README.md](new/README.md).

## Product / engineering cards (`new2/`)

Fourteen extra-domain cyclic cards (`prompt.audit.project.new2.*`) with
library-default `ALLOW_*=true`. They do **not** replace `cycle/` or `new/`.
Index: [new2/README.md](new2/README.md).

`library/audit/cycle/run/` is an incomplete same-id copy set — use `full/`
instead.
