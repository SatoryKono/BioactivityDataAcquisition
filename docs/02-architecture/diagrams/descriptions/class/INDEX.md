# Class Diagrams - Descriptions Index

_Автогенерация: 2026-07-08T10:42:35+03:00_

- Карточек описаний: **16**
- Scope: class-diagram description cards for canonical class families.

## Package-Level Diagrams (90-pkg-*.mmd)

Package-level class diagrams (90-pkg-*.mmd) are **AST-generated supplemental package-family inventory slices** that provide automated inventory of package structure. These diagrams:

- Are generated automatically from AST analysis of the codebase
- Serve as supplemental inventory slices for package families
- Do not have individual description files (by design)
- Are marked with `@reference Generated supplemental package-family diagram` in their metadata
- Should be regenerated when package structure changes

The curated class diagrams (01-16) above provide narrative documentation of key class families, while package-level diagrams (90-pkg-*.mmd) provide automated structural inventory. Both serve complementary purposes in the documentation ecosystem.

## Related Indexes

- [Diagram descriptions root index](../INDEX.md)
- [MMD diagram descriptions map](../class-summary.md)
- [Class bundle with descriptions](../../bundles/class.bundle.md)

## Cards

- [01-domain-ports](01-domain-ports.md)
- [02-entities-aggregates](02-entities-aggregates.md)
- [03-value-objects](03-value-objects.md)
- [04-types-enums](04-types-enums.md)
- [05-exceptions](05-exceptions.md)
- [06-config-classes](06-config-classes.md)
- [07-application-core-services](07-application-core-services.md)
- [08-application-services](08-application-services.md)
- [09-transformers](09-transformers.md)
- [10-adapters](10-adapters.md)
- [11-storage](11-storage.md)
- [12-composite-pipeline](12-composite-pipeline.md)
- [13-domain-services](13-domain-services.md)
- [14-observability](14-observability.md)
- [15-extractors](15-extractors.md)
- [16-factories-bootstrap](16-factories-bootstrap.md)
