# Project Rules and Standards

Project rules, coding standards, and development guidelines for BioETL.

## Documents

- **[Rules Summary](00-rules-summary.md)** — Consolidated summary of all project rules
- **[Architecture Patterns](04-architecture-and-duplication-reduction.md)** — Principles for reducing code duplication

## Key Areas

### Naming Conventions

- Documentation files: kebab-case with `NN-` prefix
- Code modules: snake_case
- Classes: PascalCase with role suffixes (Factory, Client, Impl, etc.)
- Functions: snake_case with prefixes (get_, fetch_, iter_, create_, etc.)

### ABC/Default/Impl Pattern

Three-layer pattern for all components:
- **ABC**: Contract definition
- **Default Factory**: Default implementation factory
- **Impl**: Concrete implementation

See [Rules Summary](00-rules-summary.md) section 2 for details.

### Code Style

- PEP 8 compliance
- Type annotations for public APIs
- `mypy --strict` for public APIs
- No wildcard imports
- Clean functions where possible

### Documentation Standards

- Documentation must be synchronized with code
- Auto-generated sections marked with `<!-- generated -->`
- Breaking changes documented in CHANGELOG.md

## Related Documentation

- **[Overview](../overview/)** — Introduction and key concepts
- **[Guides](../guides/)** — Practical how-to guides
- **[Reference](../reference/)** — Detailed component documentation

