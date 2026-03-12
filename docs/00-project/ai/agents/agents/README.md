# Agent Catalog — BioETL

*Статус: internal-published | Synced with `.claude/agents/` (2026-03-12)*

Consolidated agent registry. Runtime source of truth: `.claude/agents/`.

## BioETL Core (9 agents)

| Agent | Model | Role |
|-------|-------|------|
| [py-audit-bot](py-audit-bot.md) | opus | Code/architecture audit, RULES.md compliance |
| [py-plan-bot](py-plan-bot.md) | opus | Task planning, RF-* decomposition |
| [py-test-bot](py-test-bot.md) | sonnet | Tests (baseline/final/retest), coverage |
| [py-config-bot](py-config-bot.md) | sonnet | YAML configs (pipeline/DQ/filter) |
| [py-debug-bot](py-debug-bot.md) | opus | RCA, bug fixes, regression debugging |
| [py-doc-bot](py-doc-bot.md) | sonnet | Docs, ADR, CHANGELOG, Mermaid diagrams |
| [py-test-swarm](py-test-swarm.md) | opus | Hierarchical testing (L1->L2->L3) |
| [py-doc-swarm](py-doc-swarm.md) | opus | Hierarchical docs, drift detection |
| [py-review-orchestrator](py-review-orchestrator.md) | opus | Code review (S1-S8 stages) |

## Generic Utilities (12 agents)

| Agent | Model | Role |
|-------|-------|------|
| [sp-code-reviewer](sp-code-reviewer.md) | sonnet | General-purpose code review |
| [sp-debugger](sp-debugger.md) | sonnet | Bug diagnosis, root cause analysis |
| [sp-refactoring-specialist](sp-refactoring-specialist.md) | sonnet | Code refactoring |
| [sp-architect-reviewer](sp-architect-reviewer.md) | sonnet | Architecture evaluation |
| [sp-test-automator](sp-test-automator.md) | sonnet | Test framework automation |
| [sp-api-designer](sp-api-designer.md) | sonnet | API design, OpenAPI specs |
| [sp-data-engineer](sp-data-engineer.md) | sonnet | Data pipelines, ETL patterns |
| [sp-database-optimizer](sp-database-optimizer.md) | sonnet | Query optimization, indexing |
| [sp-dependency-manager](sp-dependency-manager.md) | sonnet | CVE audit, version conflicts |
| [sp-git-workflow-manager](sp-git-workflow-manager.md) | sonnet | Git branching strategies |
| [sp-prompt-engineer](sp-prompt-engineer.md) | sonnet | LLM prompt design and testing |
| [sp-scientific-literature-researcher](sp-scientific-literature-researcher.md) | sonnet | Scientific paper search (BGPT MCP) |

## Orchestration Workflow

See [ORCHESTRATION.md](ORCHESTRATION.md) for the standard 8-step workflow.
