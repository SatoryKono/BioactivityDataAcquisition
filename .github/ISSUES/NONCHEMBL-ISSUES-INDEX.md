# Non-ChEMBL Issue Drafts Index

These files are publish-ready GitHub issue drafts created from the
2026-05-19 non-ChEMBL normalization audit on `main`.

## Publish Order

### P0

1. `NONCHEMBL-001-Add-Raw-Sidecars-For-UniProt-Semantic-Payloads.md`
2. `NONCHEMBL-002-Align-Governed-OA-And-Identifier-DQ-With-Profile-Normalization.md`
3. `NONCHEMBL-003-Harden-Composite-Boundaries-Against-Non-Chembl-Normalization-Drift.md`

### P1

4. `NONCHEMBL-004-Externalize-Non-Chembl-Vocabulary-Registries-By-Family.md`
5. `NONCHEMBL-005-Standardize-Identifier-Array-Canonicalization-And-DQ.md`
6. `NONCHEMBL-006-Promote-Structured-Field-Contract-Typing-And-Hash-Governance.md`

### P2

7. `NONCHEMBL-007-Expand-Observed-Value-And-Fixture-Coverage-For-Non-Chembl-Vocabularies.md`

### Follow-up umbrella

8. `NONCHEMBL-008-Close-Remaining-Non-Chembl-Normalization-Governance-Gaps.md`

## Notes

- The issue set intentionally excludes `chembl_*` pipeline work.
- Publication-family raw provider vocabularies remain preserve-unknown unless a
  stricter policy is explicitly documented; this follows ADR-038 posture.
- The highest-risk issue is UniProt semantic payload replay/debug coverage,
  because the underlying normalization is deterministic but not yet uniformly
  forensically preserved.

## Residual Follow-Up Drafts After First-Wave Closeout

These drafts are based on the 2026-05-19 architecture-strict non-ChEMBL audit
performed after the first non-ChEMBL governance campaign was closed.

### Residual P0

9. `NONCHEMBL-009-Canonicalize-PubChem-CID-Before-Identity-Hashing-And-Composite-Boundaries.md`
10. `NONCHEMBL-010-Enforce-Shared-Publication-Taxonomy-Parity-Across-Profile-DQ-And-Gold.md`

### Residual P1

11. `NONCHEMBL-011-Add-Raw-Sidecars-For-CrossRef-Structured-Publication-Payloads.md`
12. `NONCHEMBL-012-Align-UniProt-Reference-Array-DQ-With-Profile-Owned-Canonicalization.md`

### Residual P2

13. `NONCHEMBL-013-Expand-Publication-Identifier-And-Vocabulary-Edge-Fixture-Inventory.md`
14. `NONCHEMBL-014-Resolve-Legacy-Validation-Test-Debt-Markers.md`
