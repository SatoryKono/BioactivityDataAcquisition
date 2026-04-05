# Application Layer — Navigation Map

The application layer coordinates use cases and runtime flows. It may depend on
`domain/`, but it must not own concrete I/O adapters or composition factories.

## Package Structure

| Package          | Responsibility                                                                      |
| ---------------- | ----------------------------------------------------------------------------------- |
| `core/`          | Core pipeline orchestration, runner behavior, shared execution services             |
| `composite/`     | Composite-pipeline coordination and merge-oriented workflows                        |
| `services/`      | Service objects for lifecycle, export, metadata, DQ, health, and runtime management |
| `observability/` | Application-facing observer abstractions and tracing helpers                        |
| `pipelines/`     | Pipeline-specific application flows and package-level execution seams               |

## What Belongs Here

- Use-case orchestration
- Cross-entity or cross-provider execution flows
- Service-level coordination over domain ports
- Application models used to drive pipeline runs

## What Does Not Belong Here

- Concrete HTTP, filesystem, Delta, or logging implementations
- Dependency injection and factory wiring
- Interface-layer command parsing

## Navigation Hints

- Start with `core/` for single-pipeline execution behavior.
- Start with `composite/` for multi-source or merged-runtime behavior.
- Start with `services/` when you are tracing runtime lifecycle, metadata,
  DQ, export, or shutdown flows.
