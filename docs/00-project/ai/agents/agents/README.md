______________________________________________________________________

Version: 1.0.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-23'

______________________________________________________________________

# Agent Catalog — BioETL

*Статус: internal-published | Runtime-facing mirror index (2026-03-23)*

Consolidated agent registry for published docs navigation.

## Surface Note

- This page is a **published mirror index**, not a canonical runtime registry.
- `.claude/**` is not an active runtime source until a local checkout proves
  otherwise (`AGENTS.md`). Do not treat Claude mirrors as live SSOT.
- Equal-peer runtime trees: `.codex/agents/**` and `.junie/agents/**`
  (parity via `scripts/ai/junie/check_junie_mirror.sh`). Devin uses
  `.devin/agents/**`.
- Use this catalog for discoverability; verify live runtime behavior in the
  relevant runtime tree before treating any profile note as authoritative.

## Non-Canonical Mirror Notice

`docs/00-project/ai/agents/agents/**` is a published/internal mirror surface.
It must not define runtime behavior independently from tracked runtime trees
such as `.codex/agents/**` and `.junie/agents/**`. Edit the active runtime
profile first, then refresh this mirror when behavior or contributor guidance
changes.

## BioETL Core (6 active Codex runtime agents)

Active set **MUST** match `.codex/agents/ORCHESTRATION.md` and the tracked
`py-*.md` profiles under `.codex/agents/`.

| Agent | Model | Role |
| --- | --- | --- |
| `py-audit-bot` | inherit parent | Baseline/final/targeted audit, review, debt, reproducibility (read-only) |
| `py-plan-bot` | inherit parent | Task planning, RF-\* decomposition, composite design (read-only) |
| `py-debug-bot` | inherit parent | RCA and remediation guidance (read-only) |
| `py-test-bot` | inherit parent | Tests (baseline/final/retest), coverage |
| `py-config-bot` | inherit parent | YAML configs (pipeline/DQ/filter/composite) |
| `py-doc-bot` | inherit parent | Docs, ADR, CHANGELOG, Mermaid diagrams |

Runtime mapping: `.codex/agents/CODEX-RUNTIME.md`. Production code is written by
the orchestrator directly (`py-code-bot` skill is a deprecated tombstone only).

Repo-wide documentation audits are no longer routed through a dedicated
documentation-only agent entry in active orchestration docs; use the
`py-doc-bot` / `py-doc-bot` skill surfaces for that
workflow.

## Docs-only generic utilities (archived 2026-09-04 - Wave 7)

> **Archived:** 12 sp-* profiles moved to docs/99-archive/agents-sp-2026-09/ on 2026-09-04 (zero invocations via subagent_type/spawn_agent, >70% overlap with py-*, checker missing frontmatter findings=12). Use the minimal sufficient set of 6 py-* runtime agents for BioETL tasks: py-audit-bot (audit/review), py-debug-bot (RCA), py-test-bot (tests), py-config-bot, py-doc-bot, py-plan-bot. See Wave 7 in docs/00-project/ai/agents/policy/AGENT_CONSOLIDATION_MATRIX_2026-03-08.md.

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
