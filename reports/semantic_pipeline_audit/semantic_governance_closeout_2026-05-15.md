# Semantic Governance Closeout

Generated: `2026-05-15`

## Closed Issues

- `#4217` Epic: Govern residual ETL semantic identity debt after the 2026-05-15 pipeline audit
- `#4218` Formalize ownership metadata for reviewed PARTIAL semantic identifier clusters
- `#4219` Classify and ratchet WEAK same-name semantic inventory into owned decisions
- `#4220` Add explicit ownership registry for generic lexical collision fields
- `#4221` Make composite inherited-field schema typing explicit for semantic pair rows with unknown schema
- `#4222` Enforce semantic promotion gates for canonical field registry changes

## Closeout Summary

- Extended [semantic_audit_review_registry.yaml](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/configs/field_registry/semantic_audit_review_registry.yaml:1) from simple review buckets into a machine-readable governance policy surface.
- Added explicit ownership metadata for all `PARTIAL` semantic clusters:
  - `canonical_smiles_identifier`
  - `chembl_target_identifier`
  - `inchi_key_identifier`
  - `pmc_identifier`
  - `uniprot_accession_identifier`
- Added explicit owner decisions for the high-frequency `WEAK` cluster families governed by the current review threshold.
- Added explicit generic collision policy families for:
  - `shared_description`
  - `shared_relation`
  - `shared_score`
  - `shared_type`
  - `shared_value`
- Added grouped review coverage for composite `unknown` typing rows across:
  - `composite_activity`
  - `composite_assay`
  - `composite_molecule`
  - `composite_publication`
  - `composite_target`
- Added machine-readable promotion requirements for `PARTIAL`, `WEAK`, and `CONFLICTING` status classes.

## Enforcement

- New validator command: `python -m scripts.engineering.qa check-semantic-governance-policy --check --json`
- CLI entry wired in [scripts/engineering/qa/__main__.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/engineering/qa/__main__.py:22)
- Workflow gate wired in [.github/workflows/semantic-governance.yml](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/.github/workflows/semantic-governance.yml:1)
- Regression coverage added in [test_semantic_governance_policy.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/integration/config/test_semantic_governance_policy.py:1)

## Outcome

- Residual semantic governance is now backed by explicit policy metadata plus blocking CI checks instead of only narrative review rationale.
- Canonical field promotion from `PARTIAL` or `WEAK` is now governed by explicit evidence requirements.
- Composite `unknown` typing remains allowed only where it is reviewed as inherited/system-level semantics.
