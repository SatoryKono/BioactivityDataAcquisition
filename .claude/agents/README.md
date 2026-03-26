# Claude Code Agents — BioETL

Agent registry after consolidation (2026-03-12).
See `ORCHESTRATION.md` for workflow and write-zone rules.

## BioETL Core (8 active agents)

| Agent | Model | Role |
|-------|-------|------|
| [py-audit-bot](py-audit-bot.md) | opus | Code/architecture audit, RULES.md compliance |
| [py-plan-bot](py-plan-bot.md) | opus | Task planning, RF-* decomposition |
| [py-test-bot](py-test-bot.md) | sonnet | Tests (baseline/final/retest), coverage |
| [py-config-bot](py-config-bot.md) | sonnet | YAML configs (pipeline/DQ/filter) |
| [py-debug-bot](py-debug-bot.md) | opus | RCA, bug fixes, regression debugging |
| [py-doc-bot](py-doc-bot.md) | sonnet | Docs, ADR, CHANGELOG, Mermaid diagrams |
| [py-test-swarm](py-test-swarm.md) | opus | Hierarchical testing (L1->L2->L3) |
| [py-review-orchestrator](py-review-orchestrator.md) | opus | Code review (S1-S8 stages) |

Repo-wide documentation audits are no longer routed through a dedicated
documentation-only agent entry in active orchestration docs; use the
`documentation-audit` / `documentation-cascade-audit` skill surfaces for that
workflow.

## Generic Utilities (12 agents)

| Agent | Model | Role |
|-------|-------|------|
| [code-reviewer](code-reviewer.md) | sonnet | General-purpose code review |
| [debugger](debugger.md) | sonnet | Bug diagnosis, root cause analysis |
| [refactoring-specialist](refactoring-specialist.md) | sonnet | Code refactoring |
| [architect-reviewer](architect-reviewer.md) | sonnet | Architecture evaluation |
| [test-automator](test-automator.md) | sonnet | Test framework automation |
| [api-designer](api-designer.md) | sonnet | API design, OpenAPI specs |
| [data-engineer](data-engineer.md) | sonnet | Data pipelines, ETL patterns |
| [database-optimizer](database-optimizer.md) | sonnet | Query optimization, indexing |
| [dependency-manager](dependency-manager.md) | sonnet | CVE audit, version conflicts |
| [git-workflow-manager](git-workflow-manager.md) | sonnet | Git branching strategies |
| [prompt-engineer](prompt-engineer.md) | sonnet | LLM prompt design and testing |
| [scientific-literature-researcher](scientific-literature-researcher.md) | sonnet | Scientific paper search (BGPT MCP) |

## Standard Workflow

```
1. py-audit-bot (baseline)
2. py-plan-bot
3. py-test-bot (baseline)
4. [debug cycle if FAIL]
5. code + py-config-bot (parallel)
6. py-test-bot (final)
7. py-doc-bot
8. py-audit-bot (final)
```
