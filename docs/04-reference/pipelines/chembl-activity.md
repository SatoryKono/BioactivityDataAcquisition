______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-05'

______________________________________________________________________

# Pipeline: ChEMBL Activity

This page is now a compatibility landing page for the legacy flat reference
surface under `docs/04-reference/pipelines/`.

## Current Canonical Sources

- Maintained pipeline spec:
  [chembl/05-activity-spec.md](chembl/05-activity-spec.md)
- Provider reference:
  [providers/chembl/activity.md](../providers/chembl/activity.md)
- Live config:
  `configs/entities/chembl/activity.yaml`

## Current Runtime Snapshot

| Property | Value |
| --- | --- |
| Pipeline ID | `chembl_activity` |
| Provider | `chembl` |
| Entity | `activity` |
| Silver output | Enabled |
| Gold output | Enabled |
| Source of truth | `configs/entities/chembl/activity.yaml` |

## Why This Page Is Compact

Earlier versions of this document duplicated runtime details that drifted from
the live config. The numbered spec and the provider reference are now the
maintained surfaces for current behavior.

Use this page only as a stable redirect target for old links.
