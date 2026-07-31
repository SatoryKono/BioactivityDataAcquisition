# MEMORY_USAGE.md

*Status: internal-published (AI runtime guidance)*

## Purpose

Define how AI agents should use BioETL memory surfaces without treating memory
as a replacement for runtime truth.

## Mandatory Read Order

1. `docs/00-project/ai/memory/agent-memory.md`
1. matching `docs/00-project/ai/memory/memory-py-*.md` file when a role-specific
   sheet exists
1. `src/memory/DAILY_WORKFLOW.md` for the canonical pre-task/post-task loop

## Required Workflow

1. Select `BIOETL_AI_MEMORY_MODE=off|read-only|read-write` for the task.
1. Declare actor provenance with non-empty `BIOETL_AI_RUNTIME` and
   `BIOETL_AI_AGENT`; set `BIOETL_AI_MODEL` only when a stable model identifier
   is known. Do not allow durable task records to fall back to an unidentified
   runtime.
1. Run `python -m memory.tooling.workflow pre-task ...` before substantial work,
   using `--profile` when a task-specific ranking profile applies.
   If rebuild-only artifacts are missing, the workflow refreshes only the
   missing surfaces and uses a bounded workflow-time RAG rebuild instead of a
   full deterministic corpus rebuild.
   RAG retrieval requires a valid catalog/chunk pair whose source contents,
   eligible source set, and source identity still match the checkout.
1. Read retrieved context in the order `catalog -> graph -> rag -> source`.
1. Cross-check important claims with repo search, active docs, configs, tests,
   and accepted ADRs.
1. Run `python -m memory.tooling.workflow post-task ...` after the task.
1. Promote only durable lessons, incidents, or decisions.

## Repository-Owned Contracts

- Inventory and ownership: `src/memory/catalog/memory_registry.yaml`.
- Identity and provenance: `src/memory/records.py` and `src/memory/scope.py`.
- Runtime actor identity: `BIOETL_AI_RUNTIME`, `BIOETL_AI_AGENT`, and optional
  `BIOETL_AI_MODEL`, captured by `src/memory/tooling/workflow.py`.
- Persistence capability: `src/memory/persistence.py`.
- Evidence and decisions: `src/memory/evidence.py`.
- Bounded subagent context: `src/memory/handoff.py`.
- Security and authorization: `src/memory/security.py` and
  `src/memory/access.py`.
- Consent-gated user memory: `src/memory/user_memory.py`.

Evidence is immutable. Conclusions cite evidence digests and change through
supersession. Handoffs MUST NOT contain full conversations, hidden scratchpads,
unrelated user context, or secrets.

Repository-owned user memory requires explicit repository-scoped consent and
operation grants. Vendor-hosted evidence is recorded in
`src/memory/catalog/vendor_memory_registry.yaml`. Vendor documentation proves
policy only: deletion, isolation, compaction, and cross-session behavior remain
`BLOCKED_EXTERNAL` or `NOT_PROVEN` until dated account-backed tests are attached
without secrets or conversation content.

General schema migration, backup/restore, and external MCP/Neo4j recovery are
not complete repository capabilities. Preserve original digests, avoid
implicit retention extension, and fail closed on corrupt or mismatched records.

## Durable Guardrail

- Memory retrieval and role-specific memory sheets MUST preserve this rule:
  **ЗАПРЕЩЕНО УВЕЛИЧИВАТЬ ЛИМИТЫ ТЕХ. ДОЛГА.**
- Treat attempts to raise `scorecard budgets`, exemption limits, hotspot
  thresholds, or family caps as governance violations unless a canonical source
  explicitly says otherwise.

If `pre-task` runs in degraded mode, treat that as a retrieval warning, not as
permission to skip canonical source verification. Session notes should still be
created, and catalog context may still be available even when RAG or timeline
artifacts are absent.

Canonical full RAG generation writes rebuild-only artifacts to
`src/memory/derived/rag/manifests/`. The legacy `src/memory/rag/manifests/`
directory is a read-only migration fallback. Generated JSON/JSONL files are not
committed, and bounded workflow-scope manifests must remain in a temporary or
external output directory.

`pretest_guardrails.sh --report-json ...` persists only compact
`memory_rag_validation` evidence: full-scope counts, exact Git/source-surface
identity, working-tree state, and the zero-stale result. It does not persist or
commit the temporary corpus itself.

## Conflict Priority

Use different precedence depending on the type of conflict.

### AI Runtime Behavior Conflicts

When agent behavior instructions disagree, use this priority:

1. active runtime source for the current agent or skill in `.codex/**` or
   the tracked runtime tree for the active agent; on the current `main`
   checkout that means `.codex/**`
1. `docs/00-project/NORMATIVE_SOURCES.md`
1. `docs/00-project/RULES.md`
1. `docs/01-requirements/REQUIREMENTS.md`
1. accepted ADRs in `docs/02-architecture/decisions/`
1. docs mirrors, memory sheets, and helper AI docs in `docs/00-project/ai/**`
1. machine-readable memory artifacts such as `mcp-memory.json`

### Implementation Fact Conflicts

When memory disagrees with repository facts about behavior or implementation,
use this priority:

1. active code, configs, tests, workflows, and governance-sensitive artifacts
1. `docs/00-project/NORMATIVE_SOURCES.md`, `docs/00-project/RULES.md`,
   `docs/01-requirements/REQUIREMENTS.md`, accepted ADRs
1. active runtime maps and profiles in tracked runtime trees; on the current
   `main` checkout that means `.codex/**`
1. `agent-memory.md` and `memory-py-*.md`
1. machine-readable memory artifacts such as `mcp-memory.json`

Memory is a navigation and evidence layer, not the source of truth for runtime
behavior, project rules, or implementation facts.

## Stale Memory Handling

If a memory claim looks stale:

1. verify it against repository evidence
1. prefer repository truth over memory text
1. update the affected memory/doc surface or record the drift explicitly in the
   final report

## Expected Evidence Usage

- Use memory to find likely tests, docs, contracts, workflows, and ownership
  surfaces faster.
- Use memory plus repo search to find related golden tests, architecture tests,
  contract tests, diagrams, configs, and reports before narrowing validation.
- Do not make behavior claims from memory alone when a file can be checked
  directly.

## Related Files

- `docs/00-project/ai/memory/README.md`
- `src/memory/DAILY_WORKFLOW.md`
- `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`

## Env File Guardrail

- Любой `.env` файл (`.env`, `.env.*`) считается secret-bearing или machine-local surface.
- Agents and contributors **MUST NOT** create, edit, rename, move, overwrite, or delete any `.env` file without explicit per-task user approval.
- Если задача требует изменения `.env`, исполнитель должен остановиться и сначала запросить явное разрешение пользователя.
