______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: P1
  Last verified: '2026-11-23'

______________________________________________________________________

# IUPHAR UniProt Identifier Roles (RF-002)

Contract for [#13310](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/13310)
under epic [#13308](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/13308).
Depends on RF-001 semantics
([16-iuphar-target-classification-semantics.md](16-iuphar-target-classification-semantics.md)).

This page versions the matching/normalization policy change that separates
primary UniProt anchors from auxiliary cross-references. It does **not** admit
biological accuracy (RF-008) or rewrite historical results.

Canonical machine sources:

- `src/iuphar_target_class/identifier_roles.py` (`rf002-2026-11-23`)
- `data/iuphar_target_class/rf002/matching_policy.json`
- `src/iuphar_target_class/bioetl_input.py` (`project_target_fields`)
- `src/iuphar_target_class/matching.py` (`MatchQuery.auxiliary_uniprot_ids`)
- `src/iuphar_target_class/policy.py` → `rf002_identifier_roles`

## Roles

| Role | Source | Kernel field | Matching |
| --- | --- | --- | --- |
| Primary | `component_accessions` | `uniprot` | Strict exact-channel anchors |
| Proven equivalent | xref ∩ primary | `uniprot_equivalent` | Evidence only |
| Auxiliary xref | remaining `target_xref_uniprot_ids` | `uniprot_xref` | Diagnostics only |

All original business fields remain in `source_business_data`. Match evidence
also records each accession under `primary_uniprot` /
`equivalent_uniprot` / `auxiliary_uniprot`.

## Behaviour

- Positive primary ID + unknown auxiliary xref → may still `matched`; diagnostic
  `unknown_auxiliary_uniprot`.
- Two conflicting trusted/primary IDs → `identity_conflict` (unchanged).
- Auxiliary that hits a different catalog target than a primary match →
  `auxiliary_uniprot_divergence` (warning), not `identity_conflict`.
- Name-only channels never confirm identity.
- For complexes/families: a component accession match does not prove identity of
  the whole object (`complex_component_only` / ambiguous).

## Versioning

- `matching_policy_version`: `rf002-uniprot-roles-2026-11-23`
- `legacy_matching_policy_version`: `pre-rf002-merged-uniprot-anchors`
- Profile envelopes and acceptance receipts **must** carry
  `matching_policy_version` equal to the executing adapter pin. A pre-RF-002
  receipt/profile (three version pins only, or a legacy matching token) is
  rejected at `load_profile` / `validate_acceptance_receipt`. Result provenance
  records the same pin. Independent biological admission remains RF-008.

`biological_accuracy_accepted` stays `false`.

## Legacy kernel CSV (out of scope for RF-002 re-split)

`read_bioetl_target_kernel_csv_v1` still accepts exports that only have
`uniprot` (required subset). Values in that column are treated as **primary**
anchors. Replaying an old merged-anchor CSV does **not** reconstruct
`uniprot_xref` / `uniprot_equivalent`; that replay cannot qualify RF-002 role
separation. Fresh cohort export writes the three columns. Historical CSV
re-qualification is RF-008.
