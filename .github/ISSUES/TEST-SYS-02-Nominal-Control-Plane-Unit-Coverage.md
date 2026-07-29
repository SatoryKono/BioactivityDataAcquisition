---
title: "[P0][testing] TEST-SYS-02: Nominal unit coverage for control-plane, checkpoint, registry helpers"
labels: P0, testing, control-plane, composition, coverage, architecture
assignees: []
github_issue: 7024
---

## Context

ARCH-CR2 shipped residual control-plane / storage / composition helpers. Closeout
and governance freezes protect *historical* budgets, while new helper paths still
need **nominal unit behavior tests** (not only inventory/ratchet tests).

Continues residual of **ARCH-CR2-05** (#7010).

**Audit:** `reports/grok/review_test_system_architecture_audit_20260729_FULL.md` §5 O4, P0-1  
**Epic:** TEST-SYS-00

## Problem

Architecture program adds helpers faster than closeouts retire. Risk: freeze old
issues forever while new checkpoint/registry/CLI/composite/CP paths under-assert
runtime behavior.

## Scope / modules

- `src/bioetl/application/services/control_plane/**`
- checkpoint services / facades under application + infrastructure seams
- `src/bioetl/composition/factories/**` registry validation helpers
- bronze async offload paths already touched by ARCH-CR2-01
- Tests under `tests/unit/**` with fakes/ports (no domain I/O; DI only in composition tests)

## Acceptance Criteria

- [ ] Inventory residual modules from ARCH-CR2-05 closeout + current partial-coverage CP/composition hotspots
- [ ] Add focused unit tests for success + failure paths (not assert-less stubs)
- [ ] Prefer port fakes; full Composition Root only when testing composition itself
- [ ] Module coverage inventory refreshed if `src/bioetl/**` changed (`source_tree_sha256`)
- [ ] No debt-budget growth; do not weaken determinism gates

## Related

- ARCH-CR2-05 #7010
- ARCH-CR2 closeout: `reports/quality/architecture-coderabbit-2026-07-29-arch-cr2-closeout.md`
- TEST-SYS-07 (partial coverage floors — broader)
