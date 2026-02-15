# Filter Configuration

Hierarchical filter configuration for BioETL pipelines.

*Reference: [ADR-028: Filter Rules Externalization](../../docs/02-architecture/decisions/ADR-028-filter-rules-externalization.md)*

## Structure

```
filters/
├── _defaults.yaml       # Global defaults (REQUIRED)
├── README.md            # This file
├── providers/           # Provider-level overrides
│   ├── chembl.yaml
│   ├── pubchem.yaml
│   ├── uniprot.yaml
│   ├── pubmed.yaml
│   ├── crossref.yaml
│   ├── openalex.yaml
│   └── semanticscholar.yaml
└── entities/            # Entity-specific rules
    ├── chembl/
    │   ├── activity.yaml
    │   ├── assay.yaml
    │   └── ...
    ├── pubchem/
    │   └── compound.yaml
    └── ...
```

## Merge Priority

1. `_defaults.yaml` (lowest)
1. `providers/{provider}.yaml`
1. `entities/{provider}/{entity}.yaml`
1. Inline `filter_rules` in pipeline config (highest)

## Quick Start

### Add filter for new entity

1. Create entity config:

   ```yaml
   # entities/{provider}/{entity}.yaml
   version: "1.0.0"
   provider: chembl
   entity: activity

   input_filter:
     enabled: true
     source_path: "data/input/activity.csv"
     column_name: "activity_id"
     filter_field: "activity_id"
     batch_size: 20

   gold_filters:
     required_fields:
       - activity_id
       - target_id
     columns:
       standard_type: [IC50, Ki]
   ```

1. Reference in pipeline config:

   ```yaml
   # pipelines/{provider}/{entity}.yaml
   filter_config_file: ../../filters/entities/{provider}/{entity}.yaml
   ```

### Override filter for specific pipeline

```yaml
# pipelines/{provider}/{entity}.yaml
filter_config_file: ../../filters/entities/{provider}/{entity}.yaml

# Override specific settings (optional)
filter_rules:
  input_filter:
    batch_size: 50  # Temporary override
  gold_filters:
    columns:
      standard_type: [IC50]  # More restrictive
```

## Input Filter Parameters

Input filters control which records to fetch from external APIs.

| Parameter           | Type | Description                                   |
| ------------------- | ---- | --------------------------------------------- |
| `enabled`           | bool | Enable/disable input filtering                |
| `source_path`       | str  | Path to CSV file with filter IDs              |
| `column_name`       | str  | CSV column with primary IDs                   |
| `filter_field`      | str  | API field to filter by                        |
| `batch_size`        | int  | IDs per API request (1-1000)                  |
| `fallback_column`   | str  | Optional: fallback search field (e.g., title) |
| `columns`           | list | Multi-column mode (AND logic)                 |
| `direct_filter_ids` | list | Direct IDs for composite mode                 |

### Mode Support

- **Single-column**: Filter CSV column → API field (most common)
- **Multi-column**: Multiple columns with AND-logic (hybrid server + client)
- **Direct IDs**: For composite pipelines, no CSV file needed
- **Fallback**: DOI → title mapping for publication lookup

## Gold Filter Types

Gold filters control which records pass from Silver to Gold layer.

| Filter               | Parameters          | Description                |
| -------------------- | ------------------- | -------------------------- |
| `required_fields`    | list[str]           | Fields must be non-null    |
| `columns`            | dict[str, list]     | Value inclusion list       |
| `ranges`             | dict[str, Range]    | Numeric bounds             |
| `list_lengths`       | dict[str, MinMax]   | List size constraints      |
| `list_contains`      | dict[str, Contains] | List content filter        |
| `exclude_if_present` | list[str]           | Exclude if field has value |

### Range Filter

```yaml
ranges:
  standard_value:
    min: 0
    max: 1000000
    include_min: false  # Exclude exactly 0
    include_max: true   # Include 1000000
```

### List Length Filter

```yaml
list_lengths:
  component_accessions:
    min: 1  # At least one accession
    max: 1  # Exactly one (single protein)
```

### List Contains Filter

```yaml
list_contains:
  component_types:
    values: [PROTEIN]
    mode: all  # All values must be present (or "any")
```

## Validation

```bash
# Validate all filter configs
python -c "
from pathlib import Path
import yaml
from bioetl.infrastructure.schemas.filter_config import FilterConfigFile

for f in Path('configs/filters').rglob('*.yaml'):
    if f.name.startswith('_') or f.name == 'README.md':
        continue
    with open(f) as fp:
        data = yaml.safe_load(fp)
        if data:
            FilterConfigFile.model_validate(data)
    print(f'OK {f}')
"
```

## Provider Defaults

| Provider        | Default Batch Size | Notes                    |
| --------------- | ------------------ | ------------------------ |
| ChEMBL          | 20                 | API optimal              |
| PubChem         | 1                  | SMILES search limitation |
| UniProt         | 100                | OR-query batching        |
| PubMed          | 100                | NCBI E-utilities         |
| CrossRef        | 50                 | Polite pool              |
| OpenAlex        | 50                 | Polite pool              |
| SemanticScholar | 100                | Paper lookup             |

## Entity Files

| Provider        | Entity                 | Input Filter | Gold Filters                                   |
| --------------- | ---------------------- | ------------ | ---------------------------------------------- |
| chembl          | activity               | Yes          | columns, ranges, required                      |
| chembl          | assay                  | Yes          | columns, required                              |
| chembl          | molecule               | Yes          | columns, required                              |
| chembl          | target                 | Yes          | columns, list_lengths, list_contains, required |
| chembl          | target_component       | Yes          | columns, required                              |
| chembl          | compound_record        | Yes          | required                                       |
| chembl          | publication            | Yes          | columns, ranges, required                      |
| chembl          | protein_class          | No           | columns, required                              |
| chembl          | cell_line              | Yes          | required                                       |
| chembl          | assay_parameters       | Yes          | required                                       |
| chembl          | publication_similarity | No           | ranges, required                               |
| chembl          | publication_term       | Yes          | columns, required                              |
| pubchem         | compound               | Yes          | required                                       |
| uniprot         | protein                | Yes          | columns, required                              |
| uniprot         | idmapping              | No           | required                                       |
| pubmed          | publications           | Yes          | required                                       |
| crossref        | publication            | Yes          | ranges, required                               |
| openalex        | publication            | Yes          | ranges, required                               |
| semanticscholar | publication            | Yes          | ranges, required                               |
| composite       | publication            | No           | required                                       |

## Reference

- [ADR-028: Filter Rules Externalization](../../docs/02-architecture/decisions/ADR-028-filter-rules-externalization.md)
- RULES.md Section 3: Data Quality (filter thresholds)
- Schema: `src/bioetl/infrastructure/schemas/filter_config.py`
- Loader: `src/bioetl/infrastructure/config/filter_config_loader.py`
- Domain Models: `src/bioetl/domain/filtering/`
