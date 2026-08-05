# RH6 Root Hygiene 5-Cycle Closed-Loop Report

**Program:** RH6 root hygiene minimization / registry accuracy  
**CYCLE_COUNT:** 5  
**Branch:** `agent/root-hygiene-5cycle-20260805`  
**Target:** `main`  
**Date:** 2026-08-05  
**Repo:** SatoryKono/BioactivityDataAcquisition

## Preflight

| Item | Value |
|---|---|
| Start SHA | `271a6f9c59` (main tip at branch create) |
| Worktree | `E:/github/BioactivityDataAcquisition-wt-root-hygiene` |
| Tracked root files | **37 ≡ allowlist 37** |
| Tracked root dirs | 15 validated |
| audit_root_cleanliness --strict-untracked | PASS (all cycles) |
| GitHub Issues | available |

## Before metrics

| Metric | Value |
|---|---|
| Tracked root files | 37 |
| Allowlist entries | 37 |
| Files not in allowlist | 0 |
| Registry misclassifications (FACT) | `.junie` as local-only (tracked) |
| Unregistered local clutter class | Windows `nul` |

## Cycle ledger

| Cycle | Stage1 finding | Issue | Stage3 action | Status |
|---:|---|---|---|---|
| 1 | `.junie` local-only misclassification | #7585 | reclassify to `present_curated_root_surface` | CLOSED |
| 2 | Windows `nul` clutter + registry gap; host-presence flip **rejected** by tests (#7589 not planned) | #7590 | register `nul` candidate; drop invalid `NUL` absent state | CLOSED |
| 3 | Baseline note stale vs C1/C2 | #7596 | refresh baseline narrative | CLOSED |
| 4 | AGENTS.md scratch ban omits device-name files | #7598 | extend ban text | CLOSED |
| 5 | Full re-audit; no new confirmed residual requiring change | none | no-op verification; all gates green | N/A |

## After metrics

| Metric | Value |
|---|---|
| Tracked root files | 37 ≡ allowlist |
| Allowlist expanded? | **No** |
| Debt budgets increased? | **No** |
| Agent runtime ownership | `.junie` curated peer of `.codex` confirmed |
| Local clutter policy | `nul` registered; AGENTS ban updated |

## Issue ledger

| Issue | Title | State |
|---:|---|---|
| #7585 | Registry misclassifies tracked .junie as local-only | CLOSED |
| #7589 | (mis-scoped host-presence flip) | CLOSED not_planned |
| #7590 | Windows nul local clutter registry | CLOSED |
| #7596 | Baseline note refresh | CLOSED |
| #7598 | AGENTS.md device-name ban | CLOSED |

## Residual backlog (deferred, not open issues)

- Further tracked-root shrink only after exact-root contracts drop (RH5-05/#7021 closed tracking)
- Docker adjunct rehome remains owner-gated (#6881/#6797)
- `present_local_only_root_surface` is a **policy classification**, not a host-existence snapshot (architecture tests freeze this)

## Validation gates (Cycle 5)

- `audit_root_cleanliness.py --strict-untracked` PASS
- `check_root_hygiene_review_registry.py` PASS
- `check_root_governance_docs.py` PASS
- architecture root hygiene pytest PASS

## Final status

**SUCCESS** — 5 full cycles executed with Stage1→2→3 each; confirmed findings fixed; no open RH6 blocker issues; tracked root remain 37≡allowlist without expanding budgets.
