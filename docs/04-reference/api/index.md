______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# API Reference

This section is intentionally compact in navigation to avoid exposing empty placeholder pages.

## Canonical Sources

- Architecture layer overviews:
  - [Domain](../../02-architecture/01-domain-layer.md)
  - [Application](../../02-architecture/02-application-layer.md)
  - [Infrastructure](../../02-architecture/03-infrastructure-layer.md)
  - [Composition](../../02-architecture/05-composition-layer.md)
- Source modules:
  - `src/bioetl/domain/`
  - `src/bioetl/application/`
  - `src/bioetl/infrastructure/`
  - `src/bioetl/composition/`

## Docs-as-Code Policy

- Dependency-map drift is validated in CI and pre-commit via
  `scripts/engineering/qa/generate_architecture_dependency_map.py --check`.
- Generated architecture dependency artifacts are stored in:
  - `docs/02-architecture/generated/module-dependency-map.md`
  - `docs/02-architecture/generated/module-dependency-map.json`
- The JSON summary section contains two coupling metrics:
  - `cross_layer_group_edges` — top-60 slice used in the markdown table.
- `cross_layer_group_edges_total` — full graph count before slicing; enforced by `test_cross_layer_group_edges_total_budget` with the current ratchet baseline and budget set to `287`.
