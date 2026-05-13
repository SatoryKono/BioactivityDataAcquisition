______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# ADR-005: Composition Layer as Separate Module (Not Part of Interfaces)

**Date:** 2025-12-18
**Status:** Accepted
**Decision makers:** @BioETL-Team

## Context

During architecture review, the question arose whether the `composition/` module (Composition Root, DI wiring, factories) should be merged into `interfaces/` to reduce the number of top-level directories. This decision documents the rationale for keeping them separate.

## Decision

We have chosen to **keep `composition/` as a separate top-level module**, distinct from `interfaces/`. The Composition Root is not an interface adapter but a dedicated wiring layer responsible for assembling the application's dependency graph.

```
src/bioetl/
├── domain/           # Pure business logic, Ports (Protocols)
├── application/      # Use Cases, Pipeline definitions
├── infrastructure/   # Adapters (implementations of Ports)
├── composition/      # Composition Root, DI wiring ← SEPARATE
│   ├── bootstrap/    # Bootstrap package (assembly, CLI, runtime)
│   ├── factories/
│   └── ...
└── interfaces/       # Driving Adapters (CLI, API, Orchestration)
    ├── cli/main.py   # canonical entrypoint (historical shim: cli.py)
    └── orchestration/
```

## Justification

### 1. Different Responsibilities (Single Responsibility Principle)

| Layer          | Responsibility                                        | Knows About                                                      |
| -------------- | ----------------------------------------------------- | ---------------------------------------------------------------- |
| `interfaces/`  | Handle incoming requests (CLI commands, HTTP, events) | domain, application, composition                                 |
| `composition/` | Wire dependencies, create object graph                | **ALL layers** (domain, application, infrastructure, interfaces) |

Composition Root has a unique privilege: it is the **only place** that knows about concrete infrastructure implementations and how to assemble them. Merging it into `interfaces/` would blur this distinction.

### 2. Import Matrix Preservation

Current import rules (enforced by `import-linter`):

```
From ↓ / To →        domain  application  infrastructure  composition  interfaces
─────────────────────────────────────────────────────────────────────────────────
domain                 ✅        ❌             ❌             ❌           ❌
application            ✅        ✅             ❌             ❌           ❌
infrastructure         ✅        ❌             ✅             ❌           ❌
composition            ✅        ✅             ✅             ✅           ❌
interfaces             ✅        ✅             ❌             ✅           ✅
```

> **Note (2026-05-13):** Direct `interfaces → infrastructure` imports are no longer
> part of the active import matrix. The `interfaces` layer (CLI, API handlers) must
> obtain concrete runtime wiring through `composition` entrypoints or call
> application services behind ports. `tests/architecture/test_interfaces_no_infrastructure.py`
> and `.importlinter` enforce this policy with no active legacy allowlist.

Key observation: `composition/` remains the primary DI layer. `interfaces/` must not import from `infrastructure/`; it uses `composition/` to get fully assembled objects. If we merge composition into interfaces, we:

- Lose the explicit separation of wiring concern
- Make it harder to identify where dependency assembly happens

### 3. Multiple Consumers of Composition Root

The `bootstrap` module is used by multiple entry points:

```python
# CLI (interfaces/cli/main.py)
from bioetl.composition.bootstrap.runtime.pipeline import bootstrap_pipeline_runner

runner = bootstrap_pipeline_runner(...)

# Integration Tests
from bioetl.composition.bootstrap.runtime.pipeline import bootstrap_pipeline_runner

runner = bootstrap_pipeline_runner(...)

# Future: HTTP API, Lambda handlers, etc.
```

Composition Root is **infrastructure-agnostic orchestration**, not tied to any specific interface.

### 4. Clean Architecture Alignment

In Clean Architecture (Robert C. Martin), the Composition Root is explicitly called out as a separate concern:

> "The Composition Root is the place where all the modules are composed together. It is the only place where the concrete implementations are known."

This is distinct from:

- **Controllers/Presenters** (our `interfaces/`) — handle I/O
- **Use Cases** (our `application/`) — orchestrate business logic
- **Gateways** (our `infrastructure/`) — implement ports

### 5. Explicit Architecture Documentation

A separate `composition/` directory makes the architecture self-documenting:

```
src/bioetl/
├── domain/           # "What the system IS" (entities, rules)
├── application/      # "What the system DOES" (use cases)
├── infrastructure/   # "How the system CONNECTS" (adapters)
├── composition/      # "How the system ASSEMBLES" (DI)
└── interfaces/       # "How users INTERACT" (CLI, API)
```

New developers immediately understand where dependency injection happens.

## Alternatives Considered

### Alternative 1: Merge composition/ into interfaces/

```
interfaces/
├── cli/main.py  # historical shim: cli.py
├── orchestration/
└── bootstrap/        # Moved here
    ├── __init__.py
    └── factories/
```

**Rejected because:**

- Violates SRP — interfaces would have two responsibilities
- Requires complex import rules (bootstrap can import infrastructure, but cli/main.py cannot)
- Less explicit about DI location

### Alternative 2: Merge composition/ into application/

```
application/
├── core/
├── pipelines/
└── bootstrap/        # Moved here
```

**Rejected because:**

- Application layer should not know about concrete infrastructure
- Breaks the "application depends only on ports" rule
- Would require import-linter exceptions

### Alternative 3: Rename but keep separate

```
src/bioetl/
├── ...
├── bootstrap/        # Instead of composition/
└── adapters/         # Instead of interfaces/
```

**Considered acceptable** as a cosmetic change, but not necessary. Current names are clear and follow established conventions.

## Consequences

### Positive

- Clear separation of concerns
- Import rules are simple and enforceable
- Self-documenting architecture
- Easy to add new interfaces without touching composition logic
- Testability — can test composition separately from interfaces

### Negative

- One additional top-level directory (5 instead of 4)
- Developers must understand the distinction between composition and interfaces

### Neutral

- No performance impact
- No additional dependencies

## References

- [ADR-010](ADR-010-local-only-deployment.md): Local-Only Deployment — simplified composition factories
- [ADR-011](ADR-011-remove-watermark-mechanism.md): Remove Watermark — removed watermark factories from composition
- [ADR-015](ADR-015-pipeline-services-lifecycle.md): Pipeline Services Lifecycle — services assembled in composition
- [ADR-019](ADR-019-observability-port-enforcement.md): Observability Port Enforcement — clarifies that interfaces must use LoggerPort (not structlog directly), and direct interfaces→infrastructure imports are forbidden in the active import matrix
- [ADR-020](ADR-020-basepipeline-decomposition.md): BasePipeline Decomposition — defines components that composition/ assembles
- **RULES.md §1.1**: Ports & Adapters architecture — composition implements the "glue" layer

## References

- [Clean Architecture by Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Composition Root Pattern](https://blog.ploeh.dk/2011/07/28/CompositionRoot/)
- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)

## Compliance

| Control      | Requirement                                                                | Status | Evidence                                  |
| ------------ | -------------------------------------------------------------------------- | ------ | ----------------------------------------- |
| Format       | ADR MUST use standard metadata and normalized section headings             | `pass` | `ADR-005-composition-layer-separation.md` |
| Status       | ADR status MUST be explicit and consistent                                 | `pass` | `Accepted`                                |
| Supersession | Superseded or superseding ADRs SHOULD be linked explicitly when applicable | `n/a`  | `metadata block`                          |
| Verification | Implementation and validation expectations MUST be documented              | `pass` | `Verification / Acceptance Criteria`      |
| References   | Related ADRs, docs, or artifacts SHOULD be linked                          | `pass` | `References`                              |

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
