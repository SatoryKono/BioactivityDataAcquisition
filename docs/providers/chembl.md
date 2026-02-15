# ChEMBL Provider

Data source adapter for [ChEMBL](https://www.ebi.ac.uk/chembl/) — the EMBL-EBI
chemical database of bioactive molecules with drug-like properties.

## API

- **Base URL:** `https://www.ebi.ac.uk/chembl/api/data`
- **Format:** JSON (REST API with Django-style query lookups)
- **Pagination:** `limit`/`offset` (except target, target_component, protein_class)
- **Reference:** [ChEMBL Web Services Documentation](https://chembl.gitbook.io/chembl-interface-documentation/web-services/chembl-data-web-services)

## Supported Entities

| Entity | Resource | Paginated |
|--------|----------|-----------|
| activity | `/activity.json` | Yes |
| assay | `/assay.json` | Yes |
| molecule (compound) | `/molecule.json` | Yes |
| target | `/target.json` | No |
| target_component | `/target_component.json` | No |
| document | `/document.json` | Yes |
| cell_line | `/cell_line.json` | Yes |
| protein_class | `/protein_class.json` | No |

## Extraction-Level Filtering

**Reference:** [ADR-028 §3](../02-architecture/decisions/ADR-028-filter-rules-externalization.md)

### Overview

Server-side query parameters applied at the Bronze extraction stage.
Instead of downloading the full Activity dataset (~20M records), the API
returns only records matching the configured criteria (~2–5M records),
reducing data volume by approximately 75–90%.

### Configuration

Defined in `configs/filters/entities/chembl/activity.yaml` under the
`extraction_params` key:

```yaml
extraction_params:
  # Measurement types: IC50 and Ki only
  standard_type__in: "IC50,Ki"

  # Standardized units: nanomolar
  standard_units: "nM"

  # Exact measurements only (exclude censored: >, <, ~)
  standard_relation: "="

  # Binding (B) and Functional (F) assays
  assay_type__in: "B,F"

  # Exclude potential duplicate records
  potential_duplicate: 0

  # Exclude records with data validity issues
  data_validity_comment__isnull: true

  # Only records with standardized pChEMBL value
  pchembl_value__isnull: false

  # Only ChEMBL-standardized values
  standard_flag: 1
```

### How It Works

1. Parameters are loaded from YAML config as `ExtractionParams` (frozen dataclass)
2. `ChemblAdapter._build_params()` merges extraction params into every API request
3. The resulting API URL includes all parameters:
   ```
   /chembl/api/data/activity?format=json&limit=1000&offset=0
     &standard_type__in=IC50,Ki&standard_units=nM&standard_relation==
     &assay_type__in=B,F&potential_duplicate=0
     &data_validity_comment__isnull=true&pchembl_value__isnull=false
     &standard_flag=1
   ```
4. Parameters are recorded in `SourceMetadata.query_string` for audit and reproducibility

### Audit Trail

Extraction params are logged in Bronze `SourceMetadata.query_string`, enabling:
- **Reproducibility**: exact API query can be reconstructed from metadata
- **Audit**: which filters were active during a given pipeline run
- **Debugging**: verify that server-side filtering was applied correctly

### Constraints

- Does **not** affect `content_hash` (ADR-014)
- No CLI override — deterministic per config (ADR-014)
- Provider-specific: uses ChEMBL Django-style lookups (`__in`, `__isnull`, etc.)
- Only affects Bronze extraction — Gold filters are applied separately at Silver→Gold
