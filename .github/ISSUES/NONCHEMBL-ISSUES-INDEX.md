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
