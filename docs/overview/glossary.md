# Glossary

Terminology used in BioETL documentation.

## A

**ABC (Abstract Base Class)**: A Python abstract base class that defines a contract (interface) for a component. All ABCs are documented in [Reference/ABC](../reference/abc/index.md).

**Artifact**: Output files produced by a pipeline, including data files, metadata, and QC reports.

## C

**Client**: A component that communicates with an external API (e.g., `ChemblDataClient`, `PubmedClient`).

**Contract**: The interface defined by an ABC, specifying required methods and their signatures.

## E

**Entity**: A type of data object in the domain model (e.g., `activity`, `assay`, `target`, `document`, `testitem`).

**Extractor**: A component that extracts data from a source, typically part of the Extract stage.

## F

**Factory**: A function or class that creates instances of components (e.g., `default_chembl_client()`).

## I

**Impl**: A concrete implementation of an ABC (e.g., `ChemblDataClientHTTPImpl`).

## N

**Normalizer**: A component that transforms raw data into a standardized format, typically part of the Transform stage.

## P

**Pipeline**: A data processing workflow that orchestrates extraction, transformation, validation, and writing of data.

**Provider**: The source or provider of data (e.g., `chembl`, `pubmed`, `uniprot`).

**Profile**: A named configuration profile that extends base configuration (e.g., `development`, `production`).

## S

**Schema**: A Pandera schema that defines the structure, types, and constraints for a dataset. All schemas are validated before writing.

**Stage**: A phase in the pipeline workflow (Extract, Transform, Validate, Write).

## T

**Transformer**: A component that transforms data from one format to another, typically normalizing raw API responses.

## V

**Validator**: A component that validates data against a schema, ensuring it meets the required structure and constraints.

