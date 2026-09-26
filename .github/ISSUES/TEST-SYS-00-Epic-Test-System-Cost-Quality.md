---
title: "[meta][testing] TEST-SYS-00: Epic — test system cost/quality optimization"
labels: meta, testing, architecture-tests, quality, governance, P1
assignees: []
github_issue: 7020
---

## Context

Architecture-strict audit of BioETL’s test system on `main` (2026-07-29) found
**strong architectural alignment** (scorecard testability **9.9**, **0** uncovered
modules) with primary residual risk in **cost, noise, and fixture imbalance**, not
missing hexagonal purity.

**Audit:** `reports/grok/review_test_system_architecture_audit_20260729_FULL.md`  
**Pack:** `.github/ISSUES/TEST-SYS-2026-07-29-ISSUE-PACK.md`

## Problem

- ~**22%** of test files are architecture lane; ~**16%** of those are closeout/tech-debt freezes
- VCR mass (~**139 MB** / 402) dwarfs bronze (~**1.7 MB** / 40); ChEMBL-skewed bronze
- **13/15** shards force serial workers; global xdist forbidden by design
- 744 modules partially covered (tail includes normalization/converters &lt;80%)

## Child issues

| Code | Pri | Title |
| --- | --- | --- |
| TEST-SYS-01 | P0 | Non-ChEMBL bronze exact-replay fixture promotion |
| TEST-SYS-02 | P0 | Nominal unit coverage for CP/checkpoint/registry helpers |
| TEST-SYS-03 | P1 | Architecture closeout consolidation + nightly split |
| TEST-SYS-04 | P1 | Collapse redundant S7 architecture shards |
| TEST-SYS-05 | P1 | Expand unit-parallel-safe + enforce repo_backed exclusion |
| TEST-SYS-06 | P1 | VCR size/age budget + recert workflow flag truth |
| TEST-SYS-07 | P1 | Raise floors on partial modules &lt;80% (norm/hash/identity) |
| TEST-SYS-08 | P2 | Hypothesis for identifier/normalization families |
| TEST-SYS-09 | P2 | MetricsPort/TracingPort interaction tests for top pipelines |
| TEST-SYS-10 | P2 | Basename dedup / naming hygiene |

## Acceptance Criteria

- [ ] All child issues closed or rejected with explicit rationale + evidence
- [ ] PR architecture path is lighter (closeout nightly or meta-gate) without dropping live invariants
- [ ] Determinism / domain purity / Composition Root gates remain enforced
- [ ] No technical-debt budget growth
- [ ] Publish JSON updated with final numbers: `reports/quality/test-system-audit-2026-07-29-issue-publish.json`

## Constraints

- Do **not** mandate global pytest-xdist (conflicts with `forbid_global_xdist_addopts`)
- Do **not** put I/O in domain unit tests
- Fixture deletes only via `fixture_governance_ledger` evidence rules
- Prefer Ports & Adapters fakes over composition bootstrap in pure unit tests

## Related

- Prior: TEST-AUDIT-001..019, ARCH-CR2-05 (#7010)
- Matrix SSOT: `configs/quality/test_matrix.yaml`, `configs/quality/pytest_shards.yaml`
