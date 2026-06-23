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
| `behavior/`                                                                      | Pure domain services and business rules without I/O (e.g., normalization, DQ evaluation, identity generation) |
| `schemas/`                                                                        | Pandera-backed schema contract models and schema-related contracts |
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

## ADR-048 Schema-Contract Hotspot Ownership

ADR-048 allows Pandera/Pandas only as a domain schema-contract representation
inside `schemas/` and `contracts/`. The following large schema/catalog modules
are reviewed hotspots, not general-purpose domain behavior owners:

| Path | Owner | Current role | Split-on-touch trigger | Forbidden responsibilities |
| ---- | ----- | ------------ | ---------------------- | -------------------------- |
| `src/bioetl/domain/schemas/generated/registry.py` | domain schema generated registry owner | Generated canonical registry entries from active entity schema config sections | Split provider/entity registry shards before adding non-registry logic or material growth | No runtime bootstrap, I/O, adapter wiring, or service construction |
| `src/bioetl/domain/schemas/chembl/activity.py` | ChEMBL activity schema contract owner | Pandera `ActivitySchema` DataFrameModel field contract for ChEMBL activity records | Split field-group/schema helper modules before adding transformation, normalization, or behavioral helpers | No transforms, normalization workflow, runtime compatibility patching, I/O, or adapter wiring |
| `src/bioetl/domain/schemas/_chembl_enum_catalog.py` | ChEMBL enum catalog owner | Immutable reviewed code-side vocabulary sets consumed by schema constants and profile lookup | Split provider/entity vocabulary modules before adding mutable policy, config loading, or service behavior | No config loading, file/network access, runtime service ownership, or application orchestration |

When touching these hotspots, keep ownership inside the domain schema/contract
boundary unless a future accepted ADR changes that boundary. Split only for a
concrete change or growth pressure; do not move schema ownership into
application, infrastructure, composition, or interface layers.

## Architectural Rules

- Import ports from `bioetl.domain.ports`, not internal leaf modules.
- Keep the layer free of `httpx`, `open()`, concrete loggers, or storage code.
- Preserve semantic names even when infrastructure uses different transport
  shapes underneath.
- Runtime-oriented ports such as `LoggerPort`, `RunnerFactoryPort`,
  `RunnablePort`, `RateLimiterPort`, and `CircuitBreakerPort` are sanctioned
  pure cross-layer abstractions under `docs/00-project/RULES.md`; they must not
  import concrete infrastructure or perform I/O.
- `schemas/` may use Pandera as the schema-contract representation. Treat those
  classes as validation contracts, not adapter implementations: do not add file,
  network, storage, or runtime construction logic there.
- Root-level runtime context objects such as `PipelineContext` may reference
  domain ports when the field represents an execution contract. Keep concrete
  logger/client/storage instances outside the domain layer and inject them
  through composition/application boundaries.
