# 01 Run ChEMBL Pipelines

This document describes how to run the main ChEMBL-based pipelines from the BioETL CLI.

It focuses on the conceptual contracts and typical options rather than exhaustive flag listings.

## Pipelines Covered

The following pipelines are typically exposed via dedicated run commands:

- `activity_chembl` — activity records and bioactivity measurements
- `assay_chembl` — assay-level metadata
- `target_chembl` — target entities and related components
- `document_chembl` — supporting documents and literature metadata
- `testitem_chembl` — tested items such as compounds or batches
- `chembl_all` — orchestration command to run all ChEMBL pipelines

Exact command names and options may vary between versions; always check `--help` output for your installation.

## Typical Single-Pipeline Run

A representative pattern for running a single pipeline looks like this:

```bash
bioetl run activity_chembl \
  --config configs/pipelines/activity/example.yaml
```

In this example:

- `bioetl` is the CLI entry point (replace with the actual one in your environment if it differs)
- `activity_chembl` is the pipeline code
- `--config` points to a typed YAML configuration file

Real commands may accept additional options such as profile selection or runtime overrides.

## Running All ChEMBL Pipelines

An orchestration command can be used to run all ChEMBL pipelines in a single invocation.

A conceptual example:

```bash
bioetl run chembl_all \
  --config configs/pipelines/chembl/all.yaml
```

Implementations may choose a different command structure or naming, but the idea remains the same: a single command performs a coordinated run of all relevant ChEMBL pipelines.

## Golden Runs and Determinism

Project rules define a `--golden` flag that triggers byte-for-byte comparison of outputs and QC artifacts against pre-recorded golden artifacts.

A typical pattern is:

```bash
bioetl run activity_chembl \
  --config configs/pipelines/activity/example.yaml \
  --golden
```

When `--golden` is used, any deviation from the golden artifacts should result in a non-zero exit code, causing CI to fail.

## Recommendations

- Prefer explicit, version-controlled configuration files rather than long ad-hoc command lines
- Use golden runs for critical pipelines in CI to guard against regressions
- Keep run commands idempotent so they can be safely retried

## Related Components

- **ChemblActivityPipeline**: пайплайн активности (см. `docs/02-pipelines/chembl/activity/00-activity-chembl-overview.md`)
- **PipelineBase**: базовый класс пайплайнов (см. `docs/02-pipelines/00-pipeline-base.md`)

