---
title: "[P1][testing] TEST-SYS-07: Raise floors on partial modules <80% (normalization/hash/identity)"
labels: P1, testing, coverage, determinism, domain, quality
assignees: []
github_issue: 7029
---

## Context

Module floor is excellent (**0** uncovered), but **744** modules are partially
covered. Lowest observed examples include:

- `domain/entities/bioactivity/_converters.py` ~**62%**
- normalization profile normalizers ~**74%**
- health/bootstrap __init__ partials

Replay/hash edge paths in converters/normalizers are correctness-critical.

**Audit:** `reports/grok/review_test_system_architecture_audit_20260729_FULL.md` §2.2, C2, P1-5  
**Evidence:** `reports/quality/module-coverage-inventory.json`  
**Epic:** TEST-SYS-00  
**Prior:** TEST-AUDIT-016, TDX coverage ratchets

## Problem

Formal “partial” includes many modules already &gt;95%; effort must target
**identity/hash/normalization** under **80%**, not vanity 100% everywhere.

## Scope / modules

- Inventory-driven list of modules with line coverage &lt;80% in:
  - `src/bioetl/domain/normalization/**`
  - identity/hash helpers
  - entity converters affecting content hash
- Matching `tests/unit/domain/**`

## Acceptance Criteria

- [ ] Export ranked list of &lt;80% modules in norm/hash/identity families from inventory
- [ ] Add unit tests that exercise edge branches affecting hash/order/identity
- [ ] Refresh `module-coverage-inventory.json` `source_tree_sha256` after code changes
- [ ] Do **not** raise unrelated tech-debt budgets; do not require 100% on __init__ stubs without logic
- [ ] Prefer property/table tests where branches explode (coordinate with TEST-SYS-08)

## Related

- TEST-SYS-02 (CP residual — separate surface)
- TEST-SYS-08 (Hypothesis expansion)
