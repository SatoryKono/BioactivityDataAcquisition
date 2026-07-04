______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# ADR-004: Why Pydantic over Standard Dataclasses?

**Date:** 2025-05-20
**Status:** Accepted
**Decision makers:** @BioETL-Team

## Context

The project requires a robust way to define and validate data schemas, especially for data contracts between layers (e.g., API responses, records in Delta tables). The primary candidates were standard Python `dataclasses` and Pydantic.

## Decision

We have chosen to use **Pydantic** for defining all data models and schemas throughout the application. Standard `dataclasses` should only be used for simple, internal data structures that do not require runtime validation.

This decision is codified by the inclusion of `pydantic` in `pyproject.toml` and its implicit use in data validation rules.

## Justification

While `dataclasses` provide a convenient way to create classes for storing data, Pydantic offers several critical features that are essential for a data engineering project:

1. **Runtime Data Validation**: This is the most important feature. Pydantic automatically validates incoming data at runtime against the defined types. If the data does not conform (e.g., a string is provided for an `int` field, a required field is missing), it raises a clear `ValidationError`. This is crucial for:

   - **Catching bugs early**: Detects API contract changes and data quality issues at the boundary of the system.
   - **Data Integrity**: Ensures that only clean, well-structured data enters the Silver and Gold layers.

1. **Type Coercion**: Pydantic can automatically and intelligently coerce data into the correct types. For example, if a field is declared as `int` but the input data is the string `"123"`, Pydantic will convert it to `123`. This makes the data cleaning process more robust and reduces boilerplate code.

1. **Complex Type Support**: Pydantic has built-in support for a wide range of complex types, including nested models, URLs, UUIDs, and date/time formats. This is essential for modeling real-world data from various APIs.

1. **JSON Schema Generation**: Pydantic models can be used to automatically generate JSON Schema definitions. This is a key requirement for our **Data Contracts** policy (Section 7.1 of `RULES.md`), allowing us to publish the schemas of our Gold tables for downstream consumers.

1. **Ecosystem and Integration**: Pydantic is a foundational library in the modern Python data stack, with strong integrations with frameworks like FastAPI, Pandera, and various data connectors.

## Alternatives Considered

- **Standard `dataclasses`**: While lightweight and part of the standard library, `dataclasses` provide no runtime validation or type coercion. Implementing this manually would require a significant amount of boilerplate code and would be less robust than Pydantic's battle-tested implementation.
- **`attrs`**: The `attrs` library is a powerful alternative and a precursor to `dataclasses`. It offers more features than `dataclasses` (including optional validators), but it does not have the same focus on data validation and serialization as Pydantic, nor the tight integration with the data ecosystem.

## Consequences

- **Dependency**: The project has a dependency on the Pydantic library.
- **Performance**: The runtime validation adds a small performance overhead compared to `dataclasses`. However, this is a negligible and worthwhile trade-off for the massive gains in data quality and developer productivity.

## References

- [ADR-014](ADR-014-deterministic-writes.md): Deterministic Writes — requires consistent type handling
- [ADR-018](ADR-018-gold-strict-validation.md): Gold Strict Validation — uses Pydantic/Pandera for Gold schema validation
- [ADR-021](ADR-021-ddd-aggregates-adoption.md): DDD Aggregates — uses dataclasses for domain aggregates (different concern)
- [ADR-023](ADR-023-entity-type-patterns.md): Entity Type Patterns — defines entity modeling with Pydantic

## Compliance

| Control      | Requirement                                                                | Status | Evidence                             |
| ------------ | -------------------------------------------------------------------------- | ------ | ------------------------------------ |
| Format       | ADR MUST use standard metadata and normalized section headings             | `pass` | `ADR-004-pydantic-vs-dataclasses.md` |
| Status       | ADR status MUST be explicit and consistent                                 | `pass` | `Accepted`                           |
| Supersession | Superseded or superseding ADRs SHOULD be linked explicitly when applicable | `n/a`  | `metadata block`                     |
| Verification | Implementation and validation expectations MUST be documented              | `pass` | `Verification / Acceptance Criteria` |
| References   | Related ADRs, docs, or artifacts SHOULD be linked                          | `pass` | `References`                         |

## Rollout

- Rollout steps MUST be sequenced before broad adoption.
- Documentation, configuration, and test surfaces SHOULD be updated in the same change set when the decision is implemented.
- Breaking or migration-sensitive adoption SHOULD include an explicit transition window.

## Rollback

- Rollback MUST identify the last known-good behavior or artifact set.
- If the decision changes contracts, configuration, or storage semantics, rollback SHOULD include data and compatibility checks.
- Rollback triggers SHOULD be observable through tests, runtime signals, or regression symptoms.

## Verification

- Verify architecture, configuration, and documentation changes against the current codebase.
- Run the relevant tests, validators, or parity checks before considering the ADR fully adopted.
- Confirm downstream docs and contracts reflect the same decision boundaries.

## Acceptance Criteria

- [ ] The decision is documented with current status, date, and owner metadata.
- [ ] The implementation path or adoption boundary is testable and linked from the ADR.
- [ ] Supersession or migration impact is documented when the decision changes an earlier posture.
- [ ] Related docs, contracts, and operational guidance are aligned with this ADR.
