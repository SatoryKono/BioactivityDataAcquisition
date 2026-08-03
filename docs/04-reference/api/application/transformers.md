______________________________________________________________________

# Application Transformers API Leaf

This package leaf points to transformer guidance owned by the Application layer
and provider-specific pipeline packages.

- Layer reference: [Application API](../application.md)
- Architecture context: [Application Layer](../../../02-architecture/02-application-layer.md)
- Source packages: `src/bioetl/application/core/` and
  `src/bioetl/application/pipelines/*/`
- Import guidance: use `BaseTransformer` and provider transformer modules from
  their defining packages; do not introduce cross-layer transformer aliases.

This page is intentionally compact. Use source modules for exact signatures.

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________
