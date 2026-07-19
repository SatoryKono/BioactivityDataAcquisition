______________________________________________________________________

Version: 1.0.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-12'

______________________________________________________________________

# Archived Reports Index

This directory stores superseded and historical report artifacts moved out of
`docs/reports/` so they no longer compete with the curated repo-only reports
surface.

## Current Archived Entry Set

- `audit-issues/` - historical documentation-audit issue packs and progress
  notes migrated from `docs/reports/audit-issues/`.
- `quality/` - superseded quality snapshots.
- `semantic_pipeline_audit/` - superseded semantic pipeline audit snapshots.

## Usage Rules

- Treat these files as historical evidence, not as current normative guidance.
- Resolve the one current technical-debt audit through
  `configs/quality/technical_debt_audit_registry.yaml`; dated audit files under
  `quality/` are superseded snapshots.
- Prefer `docs/reports/index.md` for the active curated reports surface.
- Prefer active documentation under `docs/00-05` for current workflows,
  architecture, contracts, and operator procedures.
- Do not edit archived report content in place unless a later retention review
  explicitly reopens the artifact.
