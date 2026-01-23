# ADR-004: Why Pydantic over Standard Dataclasses?

**Status:** Accepted
**Date:** 2025-05-20
**Decision makers:** @BioETL-Team

## Context

The project requires a robust way to define and validate data schemas, especially for data contracts between layers (e.g., API responses, records in Delta tables). The primary candidates were standard Python `dataclasses` and Pydantic.

## The Decision

We have chosen to use **Pydantic** for defining all data models and schemas throughout the application. Standard `dataclasses` should only be used for simple, internal data structures that do not require runtime validation.

This decision is codified by the inclusion of `pydantic` in `pyproject.toml` and its implicit use in data validation rules.

## Justification

While `dataclasses` provide a convenient way to create classes for storing data, Pydantic offers several critical features that are essential for a data engineering project:

1.  **Runtime Data Validation**: This is the most important feature. Pydantic automatically validates incoming data at runtime against the defined types. If the data does not conform (e.g., a string is provided for an `int` field, a required field is missing), it raises a clear `ValidationError`. This is crucial for:
    *   **Catching bugs early**: Detects API contract changes and data quality issues at the boundary of the system.
    *   **Data Integrity**: Ensures that only clean, well-structured data enters the Silver and Gold layers.

2.  **Type Coercion**: Pydantic can automatically and intelligently coerce data into the correct types. For example, if a field is declared as `int` but the input data is the string `"123"`, Pydantic will convert it to `123`. This makes the data cleaning process more robust and reduces boilerplate code.

3.  **Complex Type Support**: Pydantic has built-in support for a wide range of complex types, including nested models, URLs, UUIDs, and date/time formats. This is essential for modeling real-world data from various APIs.

4.  **JSON Schema Generation**: Pydantic models can be used to automatically generate JSON Schema definitions. This is a key requirement for our **Data Contracts** policy (Section 7.1 of `RULES.md`), allowing us to publish the schemas of our Gold tables for downstream consumers.

5.  **Ecosystem and Integration**: Pydantic is a foundational library in the modern Python data stack, with strong integrations with frameworks like FastAPI, Pandera, and various data connectors.

## Alternatives Considered

*   **Standard `dataclasses`**: While lightweight and part of the standard library, `dataclasses` provide no runtime validation or type coercion. Implementing this manually would require a significant amount of boilerplate code and would be less robust than Pydantic's battle-tested implementation.
*   **`attrs`**: The `attrs` library is a powerful alternative and a precursor to `dataclasses`. It offers more features than `dataclasses` (including optional validators), but it does not have the same focus on data validation and serialization as Pydantic, nor the tight integration with the data ecosystem.

## Consequences

*   **Dependency**: The project has a dependency on the Pydantic library.
*   **Performance**: The runtime validation adds a small performance overhead compared to `dataclasses`. However, this is a negligible and worthwhile trade-off for the massive gains in data quality and developer productivity.

## Related ADRs

- [ADR-018](ADR-018-gold-strict-validation.md): Gold Strict Validation — uses Pydantic/Pandera for Gold schema validation
- [ADR-021](ADR-021-ddd-aggregates-adoption.md): DDD Aggregates — uses dataclasses for domain aggregates (different concern)
