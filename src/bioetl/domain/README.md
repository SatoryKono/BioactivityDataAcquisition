# Domain Layer — Navigation Map

The domain layer contains the project's semantic model. It must remain pure:
no concrete I/O, no framework bootstrapping, and no dependency creation.

## Main Families

| Package                                                                           | Responsibility                                               |
| --------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| `ports/`                                                                          | Protocol-based dependency boundaries imported via the facade |
| `value_objects/`                                                                  | Immutable domain primitives and typed semantic wrappers      |
| `entities/`                                                                       | Provider- and entity-level domain records                    |
| `aggregates/`                                                                     | Aggregate roots and invariants                               |
| `services/`                                                                       | Domain services that express business rules without I/O      |
| `schemas/`                                                                        | Pandera schema models and schema-related contracts           |
| `validation/`                                                                     | Validation helpers and semantic checks                       |
| `mapping/`                                                                        | Canonical field and classification mappings                  |
| `config/`, `types/`, `exceptions/`, `registry/`, `filtering/`, `transformations/` | Supporting semantic families                                 |

## Root-Level Modules

Root-level modules in `domain/` are reserved for cross-cutting semantics that
do not yet justify their own deeper family, such as:

- shared runtime context and constants
- medallion concepts
- normalization seams used across multiple families
- serialization/resilience contracts with domain-level meaning

If a root-level concern grows into a coherent family, prefer adding or reusing
an explicit subpackage instead of flattening more modules at the package root.

## Architectural Rules

- Import ports from `bioetl.domain.ports`, not internal leaf modules.
- Keep the layer free of `httpx`, `open()`, concrete loggers, or storage code.
- Preserve semantic names even when infrastructure uses different transport
  shapes underneath.
