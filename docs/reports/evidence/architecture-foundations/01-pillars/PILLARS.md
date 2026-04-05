# Pillars

This pack collects **hierarchical architecture evidence** in three layers:

1. `layers-and-boundaries` — what each top-level project layer is responsible for
1. `architecture-patterns` — which core architectural patterns the repo explicitly uses
1. `enforcement-guardrails` — how those boundaries and patterns are kept enforceable

## layers-and-boundaries

- Priority: High
- Scope: Current `src/bioetl` top-level layer model (`domain`, `application`, `infrastructure`, `composition`, `interfaces`), their declared responsibilities, and the most important boundary expectations around them.
- Scope restrictions:
  - In scope: `README.md`, `AGENTS.md`, `docs/02-architecture/decisions/ADR-005-composition-layer-separation.md`, `docs/02-architecture/system-context.md`, `tests/architecture/test_layer_dependencies.py`, `tests/architecture/test_interfaces_no_infrastructure.py`, and current `src/bioetl` directory layout.
  - Out of scope: provider-specific pipeline internals, per-entity configs, runtime performance, and business data semantics.

### Research Questions

1. What responsibilities are assigned to each of the five top-level layers?
1. Which layer is explicitly treated as the pure business-logic core?
1. Which layer is responsible for external adapters and storage implementations?
1. Why is `composition/` separate from `interfaces/`?
1. What is the intended role of the `interfaces/` layer relative to application and composition?

## architecture-patterns

- Priority: High
- Scope: Explicit architecture styles and design patterns that the repository claims to follow and encodes in its layout and documentation.
- Scope restrictions:
  - In scope: `README.md`, `AGENTS.md`, `docs/02-architecture/system-context.md`, `docs/03-guides/registry-pattern.md`, `docs/00-project/glossary.md`, and current public composition surfaces under `src/bioetl/composition/`.
  - Out of scope: detailed provider behavior, data-quality business rules, and historical archived reviews unless an active document references them.

### Research Questions

1. Does the repository explicitly define itself as Hexagonal / Ports & Adapters?
1. How is Medallion architecture represented in active docs and storage flow?
1. Which DDD primitives are part of the domain layer?
1. How is Dependency Injection expected to work in practice?
1. Is there a registry/factory-based assembly pattern for pipelines and providers?

## enforcement-guardrails

- Priority: High
- Scope: Current docs-as-code and test guardrails that keep architectural boundaries and patterns enforceable on the active baseline.
- Scope restrictions:
  - In scope: `docs/02-architecture/generated/module-dependency-map.md`, `tests/architecture/test_layer_dependencies.py`, `tests/architecture/test_bootstrap_layer_boundaries.py`, `tests/architecture/test_composition_factory_import_boundaries.py`, `tests/architecture/test_di_runtime_inline_construction.py`, `tests/architecture/test_interfaces_no_infrastructure.py`, `tests/architecture/test_no_structlog_in_application_interfaces.py`, `tests/architecture/test_no_inline_construction_in_adapters.py`, `tests/architecture/test_factory_validator_enforcement.py`, and fresh local command outputs captured on `2026-03-20`.
  - Out of scope: full test-suite health, provider correctness, and deployment/infrastructure outside architecture-specific guardrails.

### Research Questions

1. Does the current dependency map show any layer-policy violations?
1. Do the current layer dependency tests pass on the active baseline?
1. Do bootstrap/composition boundary tests pass on the active baseline?
1. Do interface dependency and DI-hardening tests pass on the active baseline?
1. Is the import matrix merely documented, or also backed by executable guardrails?
