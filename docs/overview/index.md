# BioETL Overview

BioETL is a data processing framework for acquiring, normalizing, and validating bioactivity-related datasets from multiple external sources.

## What is BioETL?

BioETL provides a unified infrastructure for extracting data from external APIs (ChEMBL, PubMed, UniProt, etc.), transforming and normalizing it according to strict schemas, and exporting it in a deterministic, reproducible format.

## Key Concepts

- **Pipeline**: A data processing workflow that extracts, transforms, validates, and writes data from a source
- **Entity**: A type of data object (e.g., `activity`, `assay`, `target`, `document`)
- **Provider**: The source of data (e.g., `chembl`, `pubmed`, `uniprot`)
- **ABC (Abstract Base Class)**: A contract defining the interface for a component (e.g., `SourceClientABC`, `TransformerABC`)
- **Normalizer**: A component that transforms raw data into a standardized format
- **Schema**: A Pandera schema that validates data structure and types before writing

## Documentation Structure

- **[Getting Started](getting-started.md)** — Quick start guide for running your first pipeline
- **[Architecture Overview](architecture-overview.md)** — High-level system architecture and component interactions
- **[Glossary](glossary.md)** — Complete terminology reference

## Related Documentation

- **[Guides](../guides/index.md)** — Step-by-step how-to guides
- **[Reference](../reference/)** — Detailed component documentation
- **[Architecture](../architecture/)** — Architectural decisions and design patterns
- **[Project Rules](../project/)** — Coding standards and project conventions

