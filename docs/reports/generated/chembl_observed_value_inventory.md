# ChEMBL Bronze Observed Value Inventory

- source: `tracked_chembl_bronze_fixtures`
- manifest_path: `configs/base/bronze_fixture_manifest.yaml`
- fixtures_count: `15`
- field_rows_count: `245`

## Fixture Summary

- `chembl_activity` -> `11` fields from `tests/fixtures/bronze/chembl/activity/sample_ci_2026-03-25.jsonl`
- `chembl_assay` -> `29` fields from `tests/fixtures/bronze/chembl/assay/sample_ci_2026-04-24.jsonl`
- `chembl_assay_parameters` -> `29` fields from `tests/fixtures/bronze/chembl/assay_parameters/sample_ci_2026-04-30.jsonl`
- `chembl_cell_line` -> `11` fields from `tests/fixtures/bronze/chembl/cell_line/sample_ci_2026-04-29.jsonl`
- `chembl_compound_record` -> `6` fields from `tests/fixtures/bronze/chembl/compound_record/sample_ci_2026-04-29.jsonl`
- `chembl_molecule` -> `30` fields from `tests/fixtures/bronze/chembl/molecule/sample_ci_2026-03-25.jsonl`
- `chembl_protein_class` -> `10` fields from `tests/fixtures/bronze/chembl/protein_class/sample_ci_2026-04-29.jsonl`
- `chembl_publication` -> `19` fields from `tests/fixtures/bronze/chembl/publication/sample_ci_2026-04-24.jsonl`
- `chembl_publication_similarity` -> `6` fields from `tests/fixtures/bronze/chembl/publication_similarity/sample_ci_2026-04-30.jsonl`
- `chembl_publication_term` -> `19` fields from `tests/fixtures/bronze/chembl/publication_term/sample_ci_2026-04-30.jsonl`
- `chembl_subcellular_fraction` -> `29` fields from `tests/fixtures/bronze/chembl/subcellular_fraction/sample_ci_2026-04-30.jsonl`
- `chembl_target` -> `8` fields from `tests/fixtures/bronze/chembl/target/sample_ci_2026-04-24.jsonl`
- `chembl_target_component` -> `12` fields from `tests/fixtures/bronze/chembl/target_component/sample_ci_2026-04-29.jsonl`
- `chembl_target_protein_classification` -> `20` fields from `tests/fixtures/bronze/chembl/target_protein_classification/sample_ci_2026-06-01.jsonl`
- `chembl_tissue` -> `6` fields from `tests/fixtures/bronze/chembl/tissue/sample_ci_2026-04-29.jsonl`

## Sample Field Rows

- `chembl_activity.activity_id` distinct=`22` non_null=`22` examples=`ACT0001, ACT0002, ACT0003, ACT0004, ACT0005`
- `chembl_activity.bao_endpoint` distinct=`2` non_null=`2` examples=`BAO:0000190, bao_0000218`
- `chembl_activity.bao_format` distinct=`2` non_null=`2` examples=`BAO_0000218, bao:0000190`
- `chembl_activity.molecule_chembl_id` distinct=`22` non_null=`22` examples=`CHEMBL1, CHEMBL10, CHEMBL11, CHEMBL12, CHEMBL13`
- `chembl_activity.qudt_units` distinct=`2` non_null=`2` examples=`mg.kg-1, nM`
- `chembl_activity.standard_type` distinct=`3` non_null=`22` examples=`EC50, IC50, Ki`
- `chembl_activity.standard_units` distinct=`2` non_null=`2` examples=`nM, ug.mL-1`
- `chembl_activity.standard_value` distinct=`22` non_null=`22` examples=`1.2, 1.9, 10.6, 11.2, 13.5`
- `chembl_activity.target_chembl_id` distinct=`22` non_null=`22` examples=`CHEMBL_T1, CHEMBL_T10, CHEMBL_T11, CHEMBL_T12, CHEMBL_T13`
- `chembl_activity.units` distinct=`2` non_null=`2` examples=`mg/kg, nanomolar`
- `chembl_activity.uo_units` distinct=`2` non_null=`2` examples=`UO:0000065, UO_0000064`
- `chembl_assay.aidx` distinct=`1` non_null=`20` examples=`CLD0`
- `chembl_assay.assay_category` distinct=`0` non_null=`0` examples=``
- `chembl_assay.assay_cell_type` distinct=`1` non_null=`20` examples=`CHO`
- `chembl_assay.assay_chembl_id` distinct=`22` non_null=`22` examples=`CHEMBL636659, CHEMBL636660, CHEMBL636661, CHEMBL636662, CHEMBL636663`
- `chembl_assay.assay_classifications` distinct=`1` non_null=`22` examples=`[]`
- `chembl_assay.assay_group` distinct=`1` non_null=`2` examples=`BINDING`
- `chembl_assay.assay_organism` distinct=`2` non_null=`22` examples=`Homo sapiens, Rattus norvegicus`
- `chembl_assay.assay_parameters` distinct=`1` non_null=`22` examples=`[]`
- `chembl_assay.assay_strain` distinct=`0` non_null=`0` examples=``
