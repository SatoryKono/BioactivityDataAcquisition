## Canonical Sources

Read before planning or editing:

- `docs/00-project/NORMATIVE_SOURCES.md`
- `docs/00-project/RULES.md`
- `docs/01-requirements/REQUIREMENTS.md`
- `docs/02-architecture/decisions/`
- `docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`
- `AGENTS.md`

## Canonical Runtime Links

- `AGENTS.md`
- `.devin/agents/DEVIN-RUNTIME.md`
- `.devin/agents/ORCHESTRATION.md`
- `docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`

______________________________________________________________________

Version: 1.0.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-30'

______________________________________________________________________

# Agent Catalog — BioETL (Devin CLI)

*Статус: internal-published | Runtime-facing mirror index (2026-07-30)*

Consolidated agent registry for published docs navigation.

## Surface Note

- This page is a **published mirror index**, not a canonical runtime registry.
- Devin runtime source of truth is `.devin/agents/**` (see `DEVIN-RUNTIME.md`, `ORCHESTRATION.md`).
- `.codex/agents/**` is the Codex runtime reference for logical profile definitions.
- Use this catalog for discoverability; verify live runtime behavior in the relevant runtime tree before treating any profile note as authoritative.

## Non-Canonical Mirror Notice

`docs/00-project/ai/agents/agents/**` is a published/internal mirror surface. It must not define runtime behavior independently from tracked runtime trees such as `.devin/agents/**`. Edit the active runtime profile first, then refresh this mirror when behavior or contributor guidance changes.

## BioETL Core (9 active Devin runtime agents)

Active set **MUST** match `.devin/agents/ORCHESTRATION.md` and the tracked `py-*.md` profiles under `.devin/agents/`.

|| Agent                        | Model  | Role                                                                                   |
|| ---------------------------- | ------ | -------------------------------------------------------------------------------------- |
|| `py-audit-bot`               | parent | Baseline/final аудит, code review, arch guardian, API validation                       |
|| `py-architecture-debt-bot`   | parent | Architecture-debt workflow: generate → plan → execute → verify                         |
|| `py-plan-bot`                | parent | Task planning, RF-\* decomposition, composite design                                   |
|| `py-test-bot`                | swe-1.6 | Tests (baseline/final/retest), coverage                                                |
|| `py-config-bot`              | swe-1.6 | YAML configs (pipeline/DQ/filter/composite)                                            |
|| `py-debug-bot`               | parent | RCA, bug fixes, regression debugging                                                   |
|| `py-doc-bot`                 | swe-1.6 | Docs, ADR, CHANGELOG, Mermaid diagrams                                                 |
|| `py-test-swarm`              | parent | Hierarchical testing (L1→L2→L3)                                                        |
|| `py-review-orchestrator`     | parent | Hierarchical code review (S1–S8)                                                       |

Runtime mapping: `.devin/agents/DEVIN-RUNTIME.md`. Production code is written by the orchestrator directly.

Repo-wide documentation audits are routed through the `documentation-audit` / `documentation-cascade-audit` skills rather than a dedicated documentation-only subagent profile.

## Devin vs Codex Runtime

|| Aspect | Codex Runtime | Devin Runtime |
|| ------ | ------------- | ------------- |
|| Agent spawning | `spawn_agent(agent_type, message)` | `run_subagent(title, task, profile, is_background)` |
|| Built-in profiles | `default`, `explorer`, `worker` | `subagent_explore`, `subagent_general` |
|| Custom profiles | Native agent roles | Custom subagent profiles in `.devin/agents/*/AGENT.md` |
|| Model assignment | Fixed per profile (opus/sonnet) | Inherits parent model or explicit `model:` field |
|| Execution modes | Sequential/parallel | Foreground/background with permissions |

## Docs-only generic utilities (non-runtime)

The following `sp-*` profiles live only under `docs/00-project/ai/agents/agents/sp-*.md`. They are **not** Devin runtime agents: there is no `.devin/agents/sp-*.md` profile and they **MUST NOT** be spawned as if they were part of `ORCHESTRATION.md`.

|| Agent                                 | Model  | Role                               | Runtime status |
|| ------------------------------------- | ------ | ---------------------------------- | -------------- |
|| `sp-code-reviewer`                    | sonnet | General-purpose code review        | docs-only      |
|| `sp-debugger`                         | sonnet | Bug diagnosis, root cause analysis | docs-only      |
|| `sp-refactoring-specialist`           | sonnet | Code refactoring                   | docs-only      |
|| `sp-architect-reviewer`               | sonnet | Architecture evaluation            | docs-only      |
|| `sp-test-automator`                   | sonnet | Test framework automation          | docs-only      |
|| `sp-api-designer`                     | sonnet | API design, OpenAPI specs          | docs-only      |
|| `sp-data-engineer`                    | sonnet | Data pipelines, ETL patterns       | docs-only      |
|| `sp-database-optimizer`               | sonnet | Query optimization, indexing       | docs-only      |
|| `sp-dependency-manager`               | sonnet | CVE audit, version conflicts       | docs-only      |
|| `sp-git-workflow-manager`             | sonnet | Git branching strategies           | docs-only      |
|| `sp-prompt-engineer`                  | sonnet | LLM prompt design and testing      | docs-only      |
|| `sp-scientific-literature-researcher` | sonnet | Scientific paper search (BGPT MCP) | docs-only      |

## Orchestration Workflow

See [ORCHESTRATION.md](ORCHESTRATION.md) for the published mirror of the standard workflow, then confirm runtime-specific behavior in the active runtime registry when exact execution semantics matter.

Detailed profile mirrors remain repo-only under `docs/00-project/ai/agents/agents/`. When exact runtime behavior matters, prefer `.devin/agents/*.md` or the active runtime registry over the published catalog.

## Env File Guardrail

- Любой `.env` файл (`.env`, `.env.*`) считается secret-bearing или machine-local surface.
- Agents and contributors **MUST NOT** create, edit, rename, move, overwrite, or delete any `.env` file without explicit per-task user approval.
- Если задача требует изменения `.env`, исполнитель должен остановиться и сначала запросить явное разрешение пользователя.