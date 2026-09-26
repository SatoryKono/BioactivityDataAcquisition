# Agent Consolidation Matrix (Wave 1-4)

*Статус: internal-published (Internal / Extended)*

Date: 2026-03-08
Scope: `docs/00-project/ai/**`

## Goal

Reduce duplicate specialist profiles by keeping one canonical profile per function and routing deprecated entries via explicit alias mapping.

## Canonicalization Rules

1. `py-*` profiles remain dedicated BioETL runtime orchestrators/specialists.
1. `sp-*` profiles are generic specialist catalog.
1. If two `sp-*` profiles overlap >70% by responsibility, keep one canonical profile.
1. Deprecated profile must contain explicit `Canonical profile:` link.

## Wave 1 Applied

| Deprecated profile             | Canonical profile           | Action               | Status |
| ------------------------------ | --------------------------- | -------------------- | ------ |
| `sp-agent-organizer`           | `sp-workflow-orchestrator`  | alias routing        | done   |
| `sp-multi-agent-coordinator`   | `sp-workflow-orchestrator`  | alias routing        | done   |
| `sp-task-distributor`          | `sp-workflow-orchestrator`  | alias routing        | done   |
| `sp-ml-engineer`               | `sp-ai-engineer`            | alias target updated | done   |
| `sp-machine-learning-engineer` | `sp-ai-engineer`            | converted to alias   | done   |
| `sp-mobile-app-developer`      | `sp-mobile-developer`       | alias routing        | done   |
| `sp-technical-writer`          | `sp-documentation-engineer` | converted to alias   | done   |
| `sp-error-detective`           | `sp-debugger`               | converted to alias   | done   |

## Canonical Profiles Expanded In Wave 1

1. `sp-documentation-engineer` now includes technical writing mode.
1. `sp-debugger` now includes distributed RCA mode.
1. `sp-ai-engineer` now includes production ML serving mode.

## Wave 2 Applied

| Deprecated profile    | Canonical profile    | Action             | Status |
| --------------------- | -------------------- | ------------------ | ------ |
| `sp-business-analyst` | `sp-project-manager` | converted to alias | done   |

## Canonical Boundaries Hardened In Wave 2

1. `sp-project-manager` explicitly absorbs requirements/process analysis mode and routes product strategy to `sp-product-manager`.
1. `sp-code-reviewer` and `sp-architect-reviewer` are explicitly secondary to `py-audit-bot` and `py-audit-bot` for BioETL compliance.
1. `py-audit-bot` and `py-audit-bot` marked as canonical BioETL review/compliance entrypoints.

## Wave 3 Applied

| Area              | Change                                                                                                     | Status |
| ----------------- | ---------------------------------------------------------------------------------------------------------- | ------ |
| Incident handling | Added explicit escalation contract between `sp-debugger` and `sp-error-coordinator` (handoff in/out rules) | done   |
| Alias lifecycle   | Added planned removal date for all alias profiles (`2026-06-30`)                                           | done   |

## Wave 4 Applied

| Area                     | Change                                                                                      | Status |
| ------------------------ | ------------------------------------------------------------------------------------------- | ------ |
| Template standardization | Added canonical and alias templates for `sp-*` profiles                                     | done   |
| Policy checks            | Added local consolidation checker (`check_agent_consolidation.py`)                          | done   |
| Validation docs          | Added runbook for consolidation validation command                                          | done   |
| Check levels             | Split checker into `default` (baseline policy) and `--strict` (template completeness) modes | done   |

## Wave 5 Applied

| Area                            | Change                                                                                              | Status |
| ------------------------------- | --------------------------------------------------------------------------------------------------- | ------ |
| Canonical profile normalization | Added missing `Boundary note` and `Operating modes` to canonical `sp-*` profiles in snapshot mirror | done   |
| Strict validation               | `check_agent_consolidation.py --strict` now passes (`findings=0`)                                   | done   |

## Alias Retirement Schedule

| Alias profile                  | Canonical profile           | Planned removal date |
| ------------------------------ | --------------------------- | -------------------- |
| `sp-agent-organizer`           | `sp-workflow-orchestrator`  | 2026-06-30           |
| `sp-multi-agent-coordinator`   | `sp-workflow-orchestrator`  | 2026-06-30           |
| `sp-task-distributor`          | `sp-workflow-orchestrator`  | 2026-06-30           |
| `sp-mobile-app-developer`      | `sp-mobile-developer`       | 2026-06-30           |
| `sp-technical-writer`          | `sp-documentation-engineer` | 2026-06-30           |
| `sp-error-detective`           | `sp-debugger`               | 2026-06-30           |
| `sp-machine-learning-engineer` | `sp-ai-engineer`            | 2026-06-30           |
| `sp-ml-engineer`               | `sp-ai-engineer`            | 2026-06-30           |
| `sp-business-analyst`          | `sp-project-manager`        | 2026-06-30           |

## Wave 6 Applied (2026-03-12)

| Area               | Change                                                             | Status |
| ------------------ | ------------------------------------------------------------------ | ------ |
| Full consolidation | Deleted 77 generic agents from the legacy runtime agent surface    | done   |
| Mirror sync        | Deleted 77 `sp-*` mirrors from `docs/00-project/ai/agents/agents/` | done   |
| Alias retirement   | All aliases removed (ahead of 2026-06-30 schedule)                 | done   |
| Retained generic   | 12 `sp-*` profiles kept (relevant to Python ETL project)           | done   |

### Retained Generic Agents (12)

`sp-api-designer`, `sp-architect-reviewer`, `sp-code-reviewer`, `sp-data-engineer`,
`sp-database-optimizer`, `sp-debugger`, `sp-dependency-manager`, `sp-git-workflow-manager`,
`sp-prompt-engineer`, `sp-refactoring-specialist`, `sp-scientific-literature-researcher`,
`sp-test-automator`

### Deletion Criteria

- Agent never referenced in `subagent_type` calls within project
- Agent domain irrelevant to Python ETL / bioinformatics (blockchain, game-dev, IoT, PowerShell, M365, etc.)
- Agent functionality covered by existing `py-*` core agents (e.g., `sp-documentation-engineer` → `py-doc-bot`)
- Agent is a duplicate of another retained agent (e.g., `sp-error-detective` → `sp-debugger`)

### Final Inventory

| Category                                    | Count  |
| ------------------------------------------- | ------ |
| BioETL core (`py-*`)                        | 9      |
| Generic utility (`sp-*`)                    | 12     |
| Service files (ORCHESTRATION.md, README.md) | 2      |
| **Total**                                   | **23** |

## Exit Criteria For Wave 6

1. The legacy runtime agent surface contains exactly 23 files (9 py-\* + 12 generic + 2 service).
1. `docs/00-project/ai/agents/agents/` mirrors the same 23 files (with sp-\* prefix for generic).
1. No broken references in ORCHESTRATION.md, rules, or skills.
1. README.md in both locations updated to reflect new inventory.


## Wave 7 Applied (2026-09-04) — Minimal Sufficient Set

| Area | Change | Status |
| --- | --- | --- |
| Docs-only specialists | Archived 12 sp-* profiles (sp-api-designer, sp-architect-reviewer, sp-code-reviewer, sp-data-engineer, sp-database-optimizer, sp-debugger, sp-dependency-manager, sp-git-workflow-manager, sp-prompt-engineer, sp-refactoring-specialist, sp-scientific-literature-researcher, sp-test-automator) from docs/00-project/ai/agents/agents/ to docs/99-archive/agents-sp-2026-09/ | done |
| Checker evidence | check_agent_consolidation.py findings=12 (missing frontmatter) on all 12 sp-* — proved zero valid frontmatter and zero subagent_type invocations | done |
| Mirror sync | docs/00-project/ai/agents/agents/README.md updated to archived notice, 12 table rows removed | done |
| Governance | Wave 7 recorded, minimal set 6 py-* confirmed per AGENTS.md and ORCHESTRATION.md | done |

### Wave 7 Deletion Criteria (same as Wave 6, re-validated 2026-09-04)

- Agent never referenced in subagent_type/spawn_agent calls (rg 0 hits)
- Checker fails missing frontmatter on all 12 (not canonical)
- Generic domain overlap >70% with py-* core (e.g., sp-code-reviewer/sp-architect-reviewer -> py-audit-bot; sp-debugger -> py-debug-bot; sp-test-automator -> py-test-bot)
- Retained only 6 py-* runtime agents as minimal sufficient set

### Final Inventory After Wave 7

| Category | Count |
| --- | --- |
| BioETL core (py-*) | 6 |
| Generic utility (sp-*) | 0 (12 archived to docs/99-archive/agents-sp-2026-09/) |
| Service files (ORCHESTRATION.md, README.md) | 2 |
| **Total in docs/00-project/ai/agents/agents/** | **8** |

## Exit Criteria For Wave 7

1. docs/00-project/ai/agents/agents/sp-*.md = 0, docs/99-archive/agents-sp-2026-09/sp-*.md = 12
2. docs/00-project/ai/agents/agents/README.md archived notice present, no sp-* table
3. check_agent_consolidation.py after archive = 0 findings (or 0 files) and --strict PASS
4. check-links and check-drift PASS, no broken sp-* links
5. junie-mirror parity --check still PASS (no runtime change)

## Env File Guardrail

- Любой `.env` файл (`.env`, `.env.*`) считается secret-bearing или machine-local surface.
- Agents and contributors **MUST NOT** create, edit, rename, move, overwrite, or delete any `.env` file without explicit per-task user approval.
- Если задача требует изменения `.env`, исполнитель должен остановиться и сначала запросить явное разрешение пользователя.
