______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-20'

______________________________________________________________________

# Pipeline: ChEMBL Assay

This page is now a compatibility landing page for the legacy flat path
`docs/04-reference/pipelines/chembl-assay.md`.

## Current Canonical Sources

- Maintained pipeline spec:
  [chembl/06-assay-spec.md](chembl/06-assay-spec.md)
- Provider reference:
  [providers/chembl/assay.md](../providers/chembl/assay.md)
- Live config:
  `configs/entities/chembl/assay.yaml`

## Current Runtime Snapshot

| Property | Value |
| --- | --- |
| Pipeline ID | `chembl_assay` |
| Provider | `chembl` |
| Entity | `assay` |
| Silver output | Enabled |
| Gold output | Enabled |
| Gold mode | `scd2` |
| Source of truth | `configs/entities/chembl/assay.yaml` |

## Why This Page Is Compact

Earlier versions of this document duplicated runtime details that drifted from
the live config, including stale Gold write-mode text. The numbered spec and
the provider reference are now the maintained surfaces for current behavior.

Use this page only as a stable redirect target for old links.
