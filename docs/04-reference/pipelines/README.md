# Pipeline Reference

This directory contains technical reference documentation for individual pipelines.

## ChEMBL Pipelines

| Pipeline | Entity | Status |
|----------|--------|--------|
| [chembl-activity](chembl-activity.md) | Activity | Active |
| [chembl-assay](chembl-assay.md) | Assay | Active |

## Pipeline Configuration

All pipeline configurations are in `configs/pipelines/{provider}/`:

```bash
configs/pipelines/
├── chembl/
│   ├── activity.yaml
│   ├── assay.yaml
│   ├── molecule.yaml
│   └── target.yaml
├── pubchem/
│   └── compound.yaml
├── uniprot/
│   └── idmapping.yaml
└── ...
```

## Related Documentation

- [Running Pipelines](../../03-guides/running-pipelines.md)
- [Pipeline Lifecycle](../../03-guides/pipeline-lifecycle.md)
- [CLI Reference](../cli.md)
