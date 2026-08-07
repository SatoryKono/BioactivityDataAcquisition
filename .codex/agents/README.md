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
- `.codex/agents/CODEX-RUNTIME.md`
- `docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`

______________________________________________________________________

Version: 1.1.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-08-04'

______________________________________________________________________

# Agent Catalog — BioETL

*Статус: internal-published | Runtime-facing mirror index (2026-03-23)*

Consolidated agent registry for published docs navigation.

## Surface Note

- This page is a **published mirror index**, not a canonical runtime registry.
- Codex runtime source of truth is `.codex/agents/**` (see `CODEX-RUNTIME.md`,
  `ORCHESTRATION.md`). Production code is written by the orchestrator.
- `.claude/**` is **not** an active runtime source for Codex/Gemini behavior on
  `main` (see `AGENTS.md` and `AI_RUNTIME_MIRROR_OWNERSHIP.md`). Do not treat
  Claude trees as required for BioETL agent work unless a future task adds and
  verifies them.
- Use this catalog for discoverability; verify live runtime behavior in the
  relevant runtime tree before treating any profile note as authoritative.

## Non-Canonical Mirror Notice

`docs/00-project/ai/agents/agents/**` is a published/internal mirror surface.
It must not define runtime behavior independently from tracked runtime trees
such as `.codex/agents/**`. Edit the active runtime profile first, then refresh this
mirror when behavior or contributor guidance changes.

## BioETL Core (6 active Codex runtime agents)

Active set **MUST** match `.codex/agents/ORCHESTRATION.md`, the tracked
`py-*.md` behavioral profiles, and the native `py-*.toml` descriptors under
`.codex/agents/`. The descriptors inherit the parent model.

| Agent                        | Model | Role                                                                   |
| ---------------------------- | ----- | ---------------------------------------------------------------------- |
| `py-audit-bot`               | inherited | Audit, review, debt, reproducibility                               |
| `py-plan-bot`                | inherited | Task planning, RF-\* decomposition, composite design               |
| `py-test-bot`                | inherited | Focused tests, broad campaigns, coverage                           |
| `py-config-bot`              | inherited | YAML configs (pipeline/DQ/filter/composite)                        |
| `py-debug-bot`               | inherited | RCA and regression diagnosis                                      |
| `py-doc-bot`                 | inherited | Docs, broad docs audits, Mermaid diagrams                          |

Runtime mapping: `.codex/agents/CODEX-RUNTIME.md`. Production code is written by
the orchestrator directly (`py-code-bot` skill is a deprecated tombstone only).

Broad documentation audits use `py-doc-bot mode=broad`; review, debt, and broad
test work use modes of `py-audit-bot` and `py-test-bot`.

## Docs-only generic utilities (non-runtime)

The following `sp-*` profiles live only under
`docs/00-project/ai/agents/agents/sp-*.md`. They are **not** Codex runtime
agents: there is no `.codex/agents/sp-*.md` profile and they **MUST NOT** be
spawned as if they were part of `ORCHESTRATION.md`.

| Agent                                 | Model  | Role                               | Runtime status |
| ------------------------------------- | ------ | ---------------------------------- | -------------- |
| `sp-code-reviewer`                    | sonnet | General-purpose code review        | docs-only      |
| `sp-debugger`                         | sonnet | Bug diagnosis, root cause analysis | docs-only      |
| `sp-refactoring-specialist`           | sonnet | Code refactoring                   | docs-only      |
| `sp-architect-reviewer`               | sonnet | Architecture evaluation            | docs-only      |
| `sp-test-automator`                   | sonnet | Test framework automation          | docs-only      |
| `sp-api-designer`                     | sonnet | API design, OpenAPI specs          | docs-only      |
| `sp-data-engineer`                    | sonnet | Data pipelines, ETL patterns       | docs-only      |
| `sp-database-optimizer`               | sonnet | Query optimization, indexing       | docs-only      |
| `sp-dependency-manager`               | sonnet | CVE audit, version conflicts       | docs-only      |
| `sp-git-workflow-manager`             | sonnet | Git branching strategies           | docs-only      |
| `sp-prompt-engineer`                  | sonnet | LLM prompt design and testing      | docs-only      |
| `sp-scientific-literature-researcher` | sonnet | Scientific paper search (BGPT MCP) | docs-only      |

## Orchestration Workflow

See [ORCHESTRATION.md](ORCHESTRATION.md) for the published mirror of the
standard workflow, then confirm runtime-specific behavior in the active runtime
registry when exact execution semantics matter.

Detailed profile mirrors remain repo-only under `docs/00-project/ai/agents/agents/`.
When exact runtime behavior matters, prefer `.codex/agents/*.md` or the active
runtime registry over the published catalog.

## Env File Guardrail

- Любой `.env` файл (`.env`, `.env.*`) считается secret-bearing или machine-local surface.
- Agents and contributors **MUST NOT** create, edit, rename, move, overwrite, or delete any `.env` file without explicit per-task user approval.
- Если задача требует изменения `.env`, исполнитель должен остановиться и сначала запросить явное разрешение пользователя.
