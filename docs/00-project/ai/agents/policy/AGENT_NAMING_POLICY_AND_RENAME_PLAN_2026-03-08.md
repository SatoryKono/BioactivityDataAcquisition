# Agent Naming Policy And Rename Plan (Docs Scope)

*Статус: internal-published (Internal / Extended)*

Date: 2026-03-08
Scope constraint: documentation-only in `docs/00-project/ai/**` (no runtime file renames in parallel runtime agent trees or `.codex/agents`).

## 1. Problem Statement

Current agent naming mixes multiple patterns:

1. BioETL core orchestration names (`py-audit-bot`, `py-test-swarm`, `py-review-orchestrator`)
2. Generic specialist names (`backend-developer`, `risk-manager`, `data-scientist`)
3. Non-uniform suffixes (`-pro`, `-master`, `-expert`)

This reduces discoverability and increases naming drift risk.

## 2. Unified Naming Policy

### 2.1 Namespaces

1. `py-*` namespace:
   - Reserved for BioETL core orchestration agents.
   - Pattern: `py-{role}-{type}`
   - `type`: `bot | swarm | orchestrator`

2. `sp-*` namespace:
   - Generic specialist catalog.
   - Pattern: `sp-{domain}-{role}`

### 2.2 Global Rules

1. Lowercase kebab-case only.
2. `filename == frontmatter.name`.
3. Disallow new ambiguous marketing suffixes:
   - `pro`, `master`, `expert`
4. Keep guide docs outside runtime naming policy:
   - `AGENT.md`, `CLAUDE.md`, `CODEX.md`, `GEMINI.md`, `README.md`.

## 3. Proposed Rename Matrix

### 3.1 Priority P1 (must normalize)

1. `postgres-pro` -> `sp-postgres-engineer`
2. `electron-pro` -> `sp-electron-engineer`
3. `wordpress-master` -> `sp-wordpress-engineer`
4. `qa-expert` -> `sp-qa-engineer`
5. `m365-admin` -> `sp-microsoft-365-admin`
6. `architecture-techdebt-automation` -> `py-architecture-debt-bot` (if core) or `sp-architecture-debt-engineer` (if specialist)

### 3.2 Priority P2 (deduplicate semantics)

1. `ml-engineer` -> alias/deprecate to `sp-ai-engineer`
2. `mobile-app-developer` -> alias/deprecate to `sp-mobile-developer`
3. Orchestration cluster unification target:
   - canonical: `sp-workflow-orchestrator`
   - deprecate/alias candidates: `multi-agent-coordinator`, `agent-organizer`, `task-distributor`

## 4. Migration Plan (No Runtime Changes In This Scope)

### Phase A: Policy Ratification

1. Approve namespace model (`py-*`, `sp-*`).
2. Approve banned suffixes list.
3. Approve rename matrix priorities.

### Phase B: Runtime Rename Execution (outside this docs-only scope)

1. Apply renames in runtime registries.
2. Add one-release compatibility aliases.
3. Update all runtime references.

### Phase B.1: Docs Layer Alignment (completed in this scope)

Canonical docs filenames aligned:

1. `qa_orchestrator.md` -> `runtime/py-qa-orchestrator.md`
2. `diagram_docs_orchestrator.md` -> `runtime/py-diagram-docs-orchestrator.md`
3. `memory.md` -> `runtime/agent-memory.md`
4. `orchestration/ORCHESTRATION.md` -> `agents/ORCHESTRATION.md`
5. `AGENT.md` -> `guides/AGENT.md`
6. `CLAUDE.md` -> `guides/CLAUDE.md`
7. `CODEX.md` -> `guides/CODEX.md`
8. `GEMINI.md` -> `guides/GEMINI.md`

Compatibility aliases are retained at old paths as deprecated stubs.

### Phase C: Cleanup

1. Remove deprecated aliases after compatibility window.
2. Enforce via CI checks.

## 5. CI/Validation Rules (Target)

1. `filename == frontmatter.name` check.
2. Allowed prefixes: `py-` or `sp-` (except explicit guide docs).
3. Banned suffix check (`-pro`, `-master`, `-expert`).
4. Registry parity check between runtime agent catalogs where required by governance.

## 6. Wave 6 Update (2026-03-12)

All P1 renames and P2 deduplication are now superseded by full consolidation:
- 77 generic agents removed from the legacy runtime agent surface and `docs/.../agents/` (mirror)
- 12 generic agents retained (relevant to Python ETL project)
- All alias profiles removed (ahead of 2026-06-30 schedule)
- See `AGENT_CONSOLIDATION_MATRIX_2026-03-08.md` Wave 6 for details

## 7. Notes

1. This document defines policy and migration intent only.
2. Wave 6 applied runtime + docs mirror cleanup simultaneously.
3. Consolidation updates tracked in `AGENT_CONSOLIDATION_MATRIX_2026-03-08.md`.
