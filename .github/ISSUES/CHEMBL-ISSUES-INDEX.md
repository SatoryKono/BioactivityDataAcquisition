# ChEMBL Issue Drafts Index

These files are publish-ready GitHub issue drafts created from the 2026-05-08
ChEMBL normalization audit. Direct publication to GitHub was blocked in this
session because:

- GitHub app MCP startup failed
- local `gh` CLI is not installed
- `GH_TOKEN` / `GITHUB_TOKEN` were not present in the environment

## Publish Order

### P0

1. `CHEMBL-001-Align-Publication-Term-Derived-Contract.md`
2. `CHEMBL-002-Rename-ChEMBL-Taxonomy-DQ-Fields-To-Taxonomy-Id.md`
3. `CHEMBL-003-Align-Tissue-Ontology-DQ-Patterns-With-Canonical-Ids.md`
4. `CHEMBL-004-Add-Profile-Owned-Assay-Parameters-Controlled-Field-Normalization.md`
5. `CHEMBL-005-Normalize-Molecule-Type-Through-ChEMBL-Profile.md`
6. `CHEMBL-006-Enforce-One-Canonical-ChEMBL-Activity-Unit-Spelling.md`
7. `CHEMBL-007-Align-Activity-Standard-Type-With-ChEMBL-Enum-SSOT.md`
8. `CHEMBL-008-Align-Target-Type-Across-Target-Schema-DQ-And-Enum-SSOT.md`
9. `CHEMBL-009-Canonicalize-Subcellular-Fraction-Before-Identity-And-Hashing.md`
10. `CHEMBL-010-Add-Profile-Owned-Component-Type-Normalization.md`

### P1

11. `CHEMBL-011-Make-Target-Component-Json-Canonicalization-Profile-Complete.md`
12. `CHEMBL-012-Move-Publication-Type-Normalization-Into-Domain-Profile-Policy.md`
13. `CHEMBL-013-Add-SSOT-Subset-Checks-For-ChEMBL-Enum-Drift.md`

### P2

14. `CHEMBL-014-Promote-Bronze-Fixtures-For-Missing-Chembl-Pipelines.md`
15. `CHEMBL-015-Register-Missing-ChEMBL-Gold-Contracts.md`

### Follow-up umbrella

16. `CHEMBL-016-Close-Remaining-Chembl-Normalization-Governance-Gaps.md`

## Residual Follow-Up Drafts After 2026-05-19 Audit

These drafts are based on the architecture-strict ChEMBL normalization audit
performed on `main` at `2026-05-19`.

### Residual P1

17. `CHEMBL-017-Govern-ChEMBL-Molecule-Provider-Code-Surfaces-Availability-Type-And-Chirality.md`
18. `CHEMBL-018-Add-Optional-Unit-Ontology-Companion-Bundle-For-ChEMBL-Assay-Parameters.md`
19. `CHEMBL-019-Enforce-Nested-ChEMBL-Xref-Source-Vocabulary-In-Target-Structured-Fields.md`

### Residual P2

20. `CHEMBL-020-Expand-Observed-Value-Inventory-For-Weakly-Covered-ChEMBL-Reference-Pipelines.md`
21. `CHEMBL-021-Sync-ChEMBL-Provider-Docs-With-Active-Normalization-Surfaces.md`

## Notes

- As of `2026-05-29`, drafts `CHEMBL-001..021` are verified as
  `completed_in_repo` on current `main`; no active ChEMBL execution remains in
  this issue pack.
- Repo-native verification for this closeout wave:
  - `uv run python -m pytest tests/integration/config/test_chembl_policy_surface_parity.py -q`
  - `uv run python -m pytest tests/integration/config/test_chembl_observed_value_fixtures.py -q`
  - `uv run python -m pytest tests/contract/test_chembl_enum_normalization_policy.py -q`
  - `uv run python -m pytest tests/integration/normalization/test_chembl_edge_observed_values.py -q`
- The 2026-05-19 audit did not confirm a new P0 defect in determinism,
  `content_hash`, or Gold contract safety.
- The residual pack is intentionally narrower than `CHEMBL-016` and converts
  the remaining evidence-backed gaps into independently closable issues.
