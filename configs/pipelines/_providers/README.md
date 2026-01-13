# Provider-Specific Configuration Reference

This directory contains **reference documentation** for provider-specific settings.
Actual provider configurations are in `configs/sources/<provider>.yaml`.

## Configuration Hierarchy

```
configs/pipelines/_defaults.yaml     # Global defaults (DQ, sink, maintenance)
       │
       ├── configs/sources/*.yaml    # Provider HTTP/API settings (AUTHORITATIVE)
       │
       └── _providers/*.yaml         # Reference documentation (THIS DIRECTORY)
```

## Provider Files

| Provider | Source Config | Reference |
|----------|--------------|-----------|
| ChEMBL | `configs/sources/chembl.yaml` | `chembl.yaml` |
| PubChem | `configs/sources/pubchem.yaml` | `pubchem.yaml` |
| UniProt | `configs/sources/uniprot.yaml` | `uniprot.yaml` |
| CrossRef | `configs/sources/crossref.yaml` | `crossref.yaml` |
| OpenAlex | `configs/sources/openalex.yaml` | `openalex.yaml` |
| PubMed | `configs/sources/pubmed.yaml` | `pubmed.yaml` |
| SemanticScholar | `configs/sources/semanticscholar.yaml` | `semanticscholar.yaml` |

## Usage

These files are for **documentation purposes only**. Pipeline configs reference
the actual source configs via `source_file` parameter:

```yaml
# In configs/pipelines/chembl/activity.yaml
source_file: ../../sources/chembl.yaml
```

## Provider-Specific Overrides

Entity configs can override provider defaults for specific use cases:

```yaml
# Example: ID mapping with elevated DQ thresholds
dq_rules:
  soft_fail_threshold: 0.30  # 30% not_found acceptable
  hard_fail_threshold: 0.80  # 80% triggers failure
```
