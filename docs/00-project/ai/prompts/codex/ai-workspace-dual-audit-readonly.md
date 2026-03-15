# Codex Prompt: Parallel AI Workspace Audit

Source: `docs/00-project/ai/prompts/ai_workspace_setup1.md`
Purpose: deprecated reference-only dual-audit version for Codex.

## Prompt

You are Codex acting as a technical auditor of the BioETL repository structure.

Use this only when a read-only two-track audit and a refactoring plan are explicitly required. Do not edit files.

### Goal

Run two independent audits of the project structure, consolidate the results, and produce a prioritized refactoring plan.

### Hard constraints

- Read-only mode.
- Every finding must cite file or command evidence.
- Respect project architecture rules and documented exceptions.
- Analyze `tests/` and `docs/` only for source mapping and drift, not for full internal redesign.

### Audit A: structural, top-down

Check:

- directory depth hotspots
- oversized packages
- singleton packages
- empty or purely formal `__init__.py`
- symmetry across provider adapters
- source-to-test mapping coverage
- orphaned modules with no inbound usage

### Audit B: semantic, bottom-up

Check:

- SRP violations
- naming drift
- duplicated logic
- misplaced modules by architectural layer
- circular dependency clusters
- configuration sprawl
- god modules

### Consolidation

Group findings into:

- overlaps found by both audits
- unique findings found by only one audit
- conflicts requiring adjudication

For each final finding provide:

- `id`
- `category`
- `severity`
- `location`
- `description`
- `evidence`
- `recommendation`
- `confidence`

### Refactoring plan

Create RF-style tasks grouped by:

1. critical architectural blockers
2. medium-priority structural improvements
3. low-priority cleanup

Each task must include:

- goal
- linked finding IDs
- concrete action
- regression risk
- likely affected tests
- definition of done

### Output

1. Executive summary
2. Structural findings
3. Semantic findings
4. Consolidated findings matrix
5. Prioritized refactoring plan
6. Open questions and assumptions
