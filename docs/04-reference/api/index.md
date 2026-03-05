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
  `scripts/generate_architecture_dependency_map.py --check`.
- Generated architecture dependency artifacts are stored in:
  - `docs/02-architecture/generated/module-dependency-map.md`
  - `docs/02-architecture/generated/module-dependency-map.json`
