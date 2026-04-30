______________________________________________________________________

Version: 1.0.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-31'

______________________________________________________________________

# Agent Catalog — BioETL

*Статус: internal-published | Runtime-facing mirror index (2026-03-23)*

Consolidated agent registry for published docs navigation.

## Surface Note

- This page is a **published mirror index**, not a canonical runtime registry.
- Claude runtime source of truth remains in its runtime-specific agent registry.
- Codex keeps its own runtime-specific orchestration and related agent context
  under `.codex/agents/`.
- Use this catalog for discoverability; verify live runtime behavior in the
  relevant runtime tree before treating any profile note as authoritative.

## Non-Canonical Mirror Notice

`docs/00-project/ai/agents/agents/**` is a published/internal mirror surface.
It must not define runtime behavior independently from `.codex/agents/**` or
`.gemini/agents/**`. Edit the active runtime profile first, then refresh this
mirror when behavior or contributor guidance changes.

## BioETL Core (8 active agents)

| Agent                    | Model  | Role                                         |
| ------------------------ | ------ | -------------------------------------------- |
| `py-audit-bot`           | opus   | Code/architecture audit, RULES.md compliance |
| `py-plan-bot`            | opus   | Task planning, RF-\* decomposition           |
| `py-test-bot`            | sonnet | Tests (baseline/final/retest), coverage      |
| `py-config-bot`          | sonnet | YAML configs (pipeline/DQ/filter)            |
| `py-debug-bot`           | opus   | RCA, bug fixes, regression debugging         |
| `py-doc-bot`             | sonnet | Docs, ADR, CHANGELOG, Mermaid diagrams       |
| `py-test-swarm`          | opus   | Hierarchical testing (L1->L2->L3)            |
| `py-review-orchestrator` | opus   | Code review (S1-S8 stages)                   |

Repo-wide documentation audits are no longer routed through a dedicated
documentation-only agent entry in active orchestration docs; use the
`documentation-audit` / `documentation-cascade-audit` skill surfaces for that
workflow.

## Generic Utilities (12 agents)

| Agent                                 | Model  | Role                               |
| ------------------------------------- | ------ | ---------------------------------- |
| `sp-code-reviewer`                    | sonnet | General-purpose code review        |
| `sp-debugger`                         | sonnet | Bug diagnosis, root cause analysis |
| `sp-refactoring-specialist`           | sonnet | Code refactoring                   |
| `sp-architect-reviewer`               | sonnet | Architecture evaluation            |
| `sp-test-automator`                   | sonnet | Test framework automation          |
| `sp-api-designer`                     | sonnet | API design, OpenAPI specs          |
| `sp-data-engineer`                    | sonnet | Data pipelines, ETL patterns       |
| `sp-database-optimizer`               | sonnet | Query optimization, indexing       |
| `sp-dependency-manager`               | sonnet | CVE audit, version conflicts       |
| `sp-git-workflow-manager`             | sonnet | Git branching strategies           |
| `sp-prompt-engineer`                  | sonnet | LLM prompt design and testing      |
| `sp-scientific-literature-researcher` | sonnet | Scientific paper search (BGPT MCP) |

## Orchestration Workflow

See [ORCHESTRATION.md](ORCHESTRATION.md) for the published mirror of the
standard workflow, then confirm runtime-specific behavior in the active runtime
registry when exact execution semantics matter.

Detailed profile mirrors remain repo-only under `docs/00-project/ai/agents/agents/`.
When exact runtime behavior matters, prefer `.codex/agents/*.md` or the active
runtime registry over the published catalog.
