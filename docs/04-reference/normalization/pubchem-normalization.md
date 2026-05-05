______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-02'

______________________________________________________________________

# PubChem Normalization

Scope: `pubchem_compound` and the PubChem-derived anchors used by
`composite_molecule`.

Primary evidence:

- [Normalization Plan P0-P6](../../05-engineering/normalization_plan_P0_P6.md)
  plus generated matrix path
  `docs/reports/generated/pipeline_normalization_field_matrix/pipeline_normalization_field_matrix.md`
- [non_chembl_observed_values.yaml](../../../tests/fixtures/normalization/non_chembl_observed_values.yaml)
- [non_chembl_identifier_cases.yaml](../../../tests/fixtures/normalization/non_chembl_identifier_cases.yaml)
- [configs/entities/pubchem/compound.yaml](../../../configs/entities/pubchem/compound.yaml)

## Field Categories

| Field family | Governance category | Current rule |
| --- | --- | --- |
| `molecule_id` | provider identifier namespace | required business key for the compound record; not a strict enum |
| `canonical_smiles`, `isomeric_smiles`, `inchi`, `inchi_key` | raw structural identifiers | canonical text cleanup and shape validation apply; these are not vocabularies |
| `standardized_canonical_smiles`, `standardized_isomeric_smiles`, `standardized_inchi`, `standardized_inchi_key` | derived normalization anchors | normalized outputs of the standardization policy; not independent provider enums |
| `structure_parent_key` | derived normalization anchor | deterministic parent-grouping key; not a provider vocabulary |
| `chemical_standardization_status` | strict enum | bounded reviewed values from `configs/enums/pubchem.yaml` |
| `chemical_standardization_policy_version` | strict enum | bounded reviewed policy version from `configs/enums/pubchem.yaml` |
| numeric analytical fields such as `molecular_weight`, `exact_mass`, `xlogp`, `tpsa` | numeric normalization / DQ | coercion and range checks apply; these are never modeled as enums |

## Standardization Policy

Current reviewed policy:

- policy version: `pubchem-basic-v1`
- reviewed statuses:
  `standardized`, `partial`, `invalid`, `missing_structure`

These values are evidenced both in config/DQ policy and in
`non_chembl_observed_values.yaml`.

Rule: if a new PubChem standardization state is introduced, update the enum
catalog, matrix evidence, and observed-value fixture together. Do not infer a
new status ad hoc in docs or downstream code.

## Raw Structure Fields Are Not Enums

PubChem structure strings are normalization-sensitive text, not reviewed
vocabularies. That means:

- unknown but syntactically valid SMILES or InChI values are still data, not
  enum drift
- deterministic cleanup belongs in the normalization profile
- semantic grouping belongs in derived anchors such as
  `standardized_inchi_key` and `structure_parent_key`

## Raw Property URN Governance

PubChem Bronze also carries raw `props[].urn` metadata that behaves like a
provider vocabulary surface, even though it is not promoted into strict Silver
enums. The governed inventory now lives in
`configs/vocab/pubchem_property_urn.yaml` and is extracted from tracked Bronze
fixtures by `scripts/engineering/qa/extract_pubchem_property_vocab.py`.

Current governed URN fields:

- `datatype`
- `label`
- `name`
- `implementation`
- `software`
- `source`
- `release`

Rule: newly observed `props[].urn.*` values require inventory review. They must
not trigger Bronze mutation, ad hoc enum widening in domain code, or implicit
flattening into Silver.

## Composite Molecule Impact

`composite_molecule` does not re-classify PubChem compound fields into a new
closed vocabulary. Current reviewed join/anchor behavior is:

- active canonical joins include `inchi_key` and `canonical_smiles`
- retained validation anchors include `standardized_inchi_key` and
  `structure_parent_key`
- non-key PubChem compound fields remain upstream inherited in the generated
  matrix

This is why PubChem normalization changes can affect composite outputs even when
the composite config itself only changes join behavior.

## Related References

- [non-chembl-normalization-overview.md](non-chembl-normalization-overview.md)
- [PubChem provider reference](../providers/pubchem/compound.md)
