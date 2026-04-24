# Internal/Extended Material

*Status: Active | Class: internal | Last Updated: 2026-04-24*

## Purpose

This section contains internal implementation details and extended surfaces that are not part of the primary published reference documentation. This material is provided for maintainers and advanced users who need to understand implementation specifics.

## Navigation

### Internal Implementation Details

- **[Composition Layer Internal Modules](composition-internal.md)**: Internal modules like `_pipeline_execution`, `_resource_management`, `_services`
- **[Provider Registration Internals](provider-registration-internal.md)**: Internal provider config builders
- **[Extended Ports](extended-ports.md)**: Extended ports like `FilterableDataSourcePort`

### Extended Surfaces

- **[Internal Type Mappings](internal-type-mappings.md)**: Type mappings for CrossRef, OpenAlex, and other providers
- **[Implementation Patterns](implementation-patterns.md)**: Internal design patterns and conventions

## Usage Guidelines

1. **Primary vs Secondary**: Use the main reference documentation for published surfaces. Consult this section only when you need implementation details.
2. **Stability**: Internal material may change without notice and is not subject to the same compatibility guarantees as published surfaces.
3. **Audience**: Intended for maintainers, contributors, and advanced users who need to understand or modify internal implementation.

## Related Documentation

- [Main Reference Index](../index.md)
- [Architecture Overview](../../02-architecture/00-overview.md)
- [Composition Layer](../../02-architecture/05-composition-layer.md)

## Document Status

| Document | Status | Last Updated |
|----------|--------|--------------|
| composition-internal.md | Active | 2026-04-24 |
| provider-registration-internal.md | Active | 2026-04-24 |
| extended-ports.md | Active | 2026-04-24 |
| internal-type-mappings.md | Active | 2026-04-24 |
| implementation-patterns.md | Active | 2026-04-24 |
