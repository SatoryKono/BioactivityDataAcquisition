---
title: "[TEST-AUDIT] Add duplication visibility for fixtures, VCR cassettes, and golden artifacts"
github_issue: 5428
labels: enhancement, duplication, technical-debt
assignees: []
---

## Context

The repository already has fixture governance, VCR metadata inventory, and a
bounded golden-master registry. However, the standard duplication scan excludes
`tests/fixtures/**`, `*.json`, `*.yaml`, and snapshots, leaving a blind spot for
the highest-volume fixture surfaces.

## Problem

- `jscpd` does not inspect the artifacts where ETL projects typically
  accumulate copy-paste debt.
- Existing governance proves freshness and registry coverage, not duplicate
  payload detection.
- Blind duplication inside fixtures is therefore hard to measure proactively.

## Evidence

- `.jscpd.json`
- `configs/quality/test_matrix.yaml`
- `tests/fixtures/vcr/**`
- `tests/fixtures/golden/**`
- `reports/quality/vcr-metadata-catalog.json`

## Proposed Solution

1. Keep `jscpd` exclusions as-is for code duplication noise control.
2. Add a separate fixture-duplication inventory based on checksums/manifests.
3. Report duplicate or near-duplicate fixture clusters for:
   - VCR cassettes
   - golden JSON artifacts
   - tracked replay fixtures
4. Wire the inventory into an existing governance report or dedicated CI check.

## Acceptance Criteria

- [ ] Fixture duplication inventory exists for VCR/golden/tracked fixtures
- [ ] Duplicate clusters are reported in a stable machine-readable artifact
- [ ] CI or governance lane can fail or warn on newly introduced duplicate
      clusters
- [ ] Existing fixture freshness governance remains intact

## Validation

```bash
rg -n "fixture_governance|golden_master_registry|canonical_vcr_location" \
  configs/quality/test_matrix.yaml
# plus the new fixture-duplication report command introduced by this issue
```

## Risks

- Naive duplication detection may over-report intentionally similar fixtures.
- The inventory needs a clear allowlist/exception story to stay actionable.
