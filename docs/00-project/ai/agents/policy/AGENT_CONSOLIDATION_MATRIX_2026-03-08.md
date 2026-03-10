# Agent Consolidation Matrix (Wave 1-4)

*Статус: internal-published (Internal / Extended)*

Date: 2026-03-08
Scope: `docs/00-project/ai/**`

## Goal

Reduce duplicate specialist profiles by keeping one canonical profile per function and routing deprecated entries via explicit alias mapping.

## Canonicalization Rules

1. `py-*` profiles remain dedicated BioETL runtime orchestrators/specialists.
2. `sp-*` profiles are generic specialist catalog.
3. If two `sp-*` profiles overlap >70% by responsibility, keep one canonical profile.
4. Deprecated profile must contain explicit `Canonical profile:` link.

## Wave 1 Applied

| Deprecated profile | Canonical profile | Action | Status |
| --- | --- | --- | --- |
| `sp-agent-organizer` | `sp-workflow-orchestrator` | alias routing | done |
| `sp-multi-agent-coordinator` | `sp-workflow-orchestrator` | alias routing | done |
| `sp-task-distributor` | `sp-workflow-orchestrator` | alias routing | done |
| `sp-ml-engineer` | `sp-ai-engineer` | alias target updated | done |
| `sp-machine-learning-engineer` | `sp-ai-engineer` | converted to alias | done |
| `sp-mobile-app-developer` | `sp-mobile-developer` | alias routing | done |
| `sp-technical-writer` | `sp-documentation-engineer` | converted to alias | done |
| `sp-error-detective` | `sp-debugger` | converted to alias | done |

## Canonical Profiles Expanded In Wave 1

1. `sp-documentation-engineer` now includes technical writing mode.
2. `sp-debugger` now includes distributed RCA mode.
3. `sp-ai-engineer` now includes production ML serving mode.

## Wave 2 Applied

| Deprecated profile | Canonical profile | Action | Status |
| --- | --- | --- | --- |
| `sp-business-analyst` | `sp-project-manager` | converted to alias | done |

## Canonical Boundaries Hardened In Wave 2

1. `sp-project-manager` explicitly absorbs requirements/process analysis mode and routes product strategy to `sp-product-manager`.
2. `sp-code-reviewer` and `sp-architect-reviewer` are explicitly secondary to `py-review-orchestrator` and `py-audit-bot` for BioETL compliance.
3. `py-review-orchestrator` and `py-audit-bot` marked as canonical BioETL review/compliance entrypoints.

## Wave 3 Applied

| Area | Change | Status |
| --- | --- | --- |
| Incident handling | Added explicit escalation contract between `sp-debugger` and `sp-error-coordinator` (handoff in/out rules) | done |
| Alias lifecycle | Added planned removal date for all alias profiles (`2026-06-30`) | done |

## Wave 4 Applied

| Area | Change | Status |
| --- | --- | --- |
| Template standardization | Added canonical and alias templates for `sp-*` profiles | done |
| Policy checks | Added local consolidation checker (`check_agent_consolidation.py`) | done |
| Validation docs | Added runbook for consolidation validation command | done |
| Check levels | Split checker into `default` (baseline policy) and `--strict` (template completeness) modes | done |

## Wave 5 Applied

| Area | Change | Status |
| --- | --- | --- |
| Canonical profile normalization | Added missing `Boundary note` and `Operating modes` to canonical `sp-*` profiles in snapshot mirror | done |
| Strict validation | `check_agent_consolidation.py --strict` now passes (`findings=0`) | done |

## Alias Retirement Schedule

| Alias profile | Canonical profile | Planned removal date |
| --- | --- | --- |
| `sp-agent-organizer` | `sp-workflow-orchestrator` | 2026-06-30 |
| `sp-multi-agent-coordinator` | `sp-workflow-orchestrator` | 2026-06-30 |
| `sp-task-distributor` | `sp-workflow-orchestrator` | 2026-06-30 |
| `sp-mobile-app-developer` | `sp-mobile-developer` | 2026-06-30 |
| `sp-technical-writer` | `sp-documentation-engineer` | 2026-06-30 |
| `sp-error-detective` | `sp-debugger` | 2026-06-30 |
| `sp-machine-learning-engineer` | `sp-ai-engineer` | 2026-06-30 |
| `sp-ml-engineer` | `sp-ai-engineer` | 2026-06-30 |
| `sp-business-analyst` | `sp-project-manager` | 2026-06-30 |

## Next Wave Candidates

1. Wire consolidation checker into repository CI pipeline.
2. Remove alias profiles after planned date and update collected index accordingly.
3. Add auto-fix mode for stale alias removal date.

## Exit Criteria For Wave 5

1. No duplicate non-canonical profiles without explicit alias marker.
2. Routing docs reference canonical profiles by default.
3. Review/compliance flow defaults to `py-review-orchestrator` + `py-audit-bot`.
4. All alias profiles include planned removal date and canonical pointer.
5. Consolidation checker is executed automatically in CI.
