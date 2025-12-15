# Pipeline: ChEMBL Activity

This document provides details for the `chembl_activity` pipeline.

*   **Provider**: ChEMBL
*   **Entity**: Activity
*   **Configuration**: `configs/pipelines/chembl_activity.yaml`

## Description

This pipeline extracts bioactivity data from the ChEMBL database. It fetches records based on activity assays and links them to molecules and targets.

## Data Schema (Silver Layer)

The following is a simplified representation of the main fields in the Silver Delta table.

| Field Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| `activity_id` | `bigint` | Unique identifier for the activity record. | `12345` |
| `assay_id` | `string` | ChEMBL ID of the assay. | `CHEMBL67890` |
| `molecule_chembl_id` | `string` | ChEMBL ID of the tested molecule. | `CHEMBL123` |
| `target_chembl_id` | `string` | ChEMBL ID of the biological target. | `CHEMBL456` |
| `standard_type` | `string` | The standardized type of measurement (e.g., 'IC50', 'Ki'). | `'IC50'` |
| `standard_value` | `double` | The standardized value of the measurement. | `10.5` |
| `standard_units` | `string` | The standardized units of the measurement (e.g., 'nM'). | `'nM'` |
| `pchembl_value` | `double` | The pChEMBL value (-log10 of the molar activity). | `8.0` |
| `data_validity_comment` | `string` | Comment on the validity of the data point. | `'Outside typical range'` |
| `_source_batch_id` | `string` | Internal ID linking to the source Bronze batch. | `uuid...` |

## Data Quality Rules

In addition to the global DQ rules, this pipeline has the following specific checks:

1.  **`standard_value` must be positive**: `standard_value` cannot be zero or negative. Records failing this check are sent to quarantine with error code `INVALID_STANDARD_VALUE`.
2.  **`standard_type` known enum**: `standard_type` is checked against a known list of common activity types. If it's an unknown type, a warning is logged, but the record is still processed.
3.  **Molecule ID format**: `molecule_chembl_id` must match the regex pattern `^CHEMBL\d+$`.

## Example API Query

The underlying adapter uses the `chembl_webresource_client` to fetch data. A simplified query looks like this:

```python
from chembl_webresource_client.new_client import new_client

activity = new_client.activity
results = activity.filter(
    pchembl_value__isnull=False,
    assay_type='B'
).only(
    'activity_id', 'assay_chembl_id', 'molecule_chembl_id', 'target_chembl_id',
    'standard_type', 'standard_value', 'standard_units', 'pchembl_value'
)
```
