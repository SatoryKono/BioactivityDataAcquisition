# Agent Naming Policy And Rename Plan (Docs Scope)

*Статус: internal-published (Internal / Extended)*

Date: 2026-03-08
Scope constraint: documentation-only in `docs/00-project/ai/**` (no runtime file renames in parallel runtime agent trees or `.codex/agents`).

## 1. Problem Statement

Current agent naming mixes multiple patterns:

1. BioETL core orchestration names (`py-audit-bot`, `py-test-swarm`, `py-review-orchestrator`)
1. Generic specialist names (`backend-developer`, `risk-manager`, `data-scientist`)
1. Non-uniform suffixes (`-pro`, `-master`, `-expert`)

This reduces discoverability and increases naming drift risk.

## 2. Unified Naming Policy

### 2.1 Namespaces

1. `py-*` namespace:

   - Reserved for BioETL core orchestration agents.
   - Pattern: `py-{role}-{type}`
   - `type`: `bot | swarm | orchestrator`

1. `sp-*` namespace:

   - Generic specialist catalog.
   - Pattern: `sp-{domain}-{role}`

### 2.2 Global Rules

1. Lowercase kebab-case only.
1. `filename == frontmatter.name`.
1. Disallow new ambiguous marketing suffixes:
   - `pro`, `master`, `expert`
1. Keep guide docs outside runtime naming policy:
   - `AGENT.md`, `CLAUDE.md`, `CODEX.md`, `GEMINI.md`, `README.md`.

## 3. Proposed Rename Matrix

### 3.1 Priority P1 (must normalize)

1. `postgres-pro` -> `sp-postgres-engineer`
1. `electron-pro` -> `sp-electron-engineer`
1. `wordpress-master` -> `sp-wordpress-engineer`
1. `qa-expert` -> `sp-qa-engineer`
1. `m365-admin` -> `sp-microsoft-365-admin`
1. `architecture-techdebt-automation` -> `py-architecture-debt-bot` (if core) or `sp-architecture-debt-engineer` (if specialist)

Implementation status update:

- Runtime consolidation now uses `py-architecture-debt-bot` as the canonical BioETL architecture-debt workflow surface.
- `architecture-techdebt-automation` remains only as a deprecated generator-only compatibility profile.

### 3.2 Priority P2 (deduplicate semantics)

1. `ml-engineer` -> alias/deprecate to `sp-ai-engineer`
1. `mobile-app-developer` -> alias/deprecate to `sp-mobile-developer`
1. Orchestration cluster unification target:
   - canonical: `sp-workflow-orchestrator`
   - deprecate/alias candidates: `multi-agent-coordinator`, `agent-organizer`, `task-distributor`

## 4. Migration Plan (No Runtime Changes In This Scope)

### Phase A: Policy Ratification

1. Approve namespace model (`py-*`, `sp-*`).
1. Approve banned suffixes list.
1. Approve rename matrix priorities.

### Phase B: Runtime Rename Execution (outside this docs-only scope)

1. Apply renames in runtime registries.
1. Add one-release compatibility aliases.
1. Update all runtime references.

### Phase B.1: Docs Layer Alignment (completed in this scope)

Canonical docs filenames aligned:

1. `qa_orchestrator.md` -> `runtime/py-qa-orchestrator.md`
1. `diagram_docs_orchestrator.md` -> `runtime/py-diagram-docs-orchestrator.md`
1. `memory.md` -> `docs/00-project/ai/memory/agent-memory.md`
1. `orchestration/ORCHESTRATION.md` -> `agents/ORCHESTRATION.md`
1. `AGENT.md` -> `guides/AGENT.md`
1. `CLAUDE.md` -> `guides/CLAUDE.md`
1. `CODEX.md` -> `guides/CODEX.md`
1. `GEMINI.md` -> `guides/GEMINI.md`

Compatibility aliases are retained at old paths as deprecated stubs.

### Phase C: Cleanup

1. Remove deprecated aliases after compatibility window.
1. Enforce via CI checks.

## 5. CI/Validation Rules (Target)

1. `filename == frontmatter.name` check.
1. Allowed prefixes: `py-` or `sp-` (except explicit guide docs).
1. Banned suffix check (`-pro`, `-master`, `-expert`).
1. Registry parity check between runtime agent catalogs where required by governance.

## 6. Wave 6 Update (2026-03-12)

All P1 renames and P2 deduplication are now superseded by full consolidation:

- 77 generic agents removed from the legacy runtime agent surface and `docs/.../agents/` (mirror)
- 12 generic agents retained (relevant to Python ETL project)
- All alias profiles removed (ahead of 2026-06-30 schedule)
- See `AGENT_CONSOLIDATION_MATRIX_2026-03-08.md` Wave 6 for details

## 7. Notes

1. This document defines policy and migration intent only.
1. Wave 6 applied runtime + docs mirror cleanup simultaneously.
1. Consolidation updates tracked in `AGENT_CONSOLIDATION_MATRIX_2026-03-08.md`.
