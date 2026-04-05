# Сбор evidence завершён: architecture-foundations

Review note (2026-03-27): included in the repo-wide evidence-pack sweep; see `docs/reports/evidence/project-evidence-rebaseline/06-status/EVIDENCE-PACK-REVIEW-2026-03-27.md` for wave status, retained-vs-reopened interpretation, and current review scope.

**Создано объектов evidence:** 15
**Gate Статус:** PASSED

Revalidated against the current repository state on 2026-03-23.

Примечание о rebaseline: after `RF-011`, the full verify baseline reconfirmed
that the dependency-map checks, architecture suites, and related enforcement
guardrails are green on the active tree.

## Сводка evidence

| ID                                                            | Claim Summary                                                                                                    | Confidence |
| ------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- | ---------- |
| EV-layers-domain-pure-business-logic-no-io                    | Domain is the pure business-logic core and is guarded against I/O/application/infrastructure imports.            | 0.97       |
| EV-layers-application-owns-orchestration-and-services         | Application owns orchestration, runners, transformers, and services rather than concrete wiring.                 | 0.94       |
| EV-layers-infrastructure-hosts-adapters-storage-observability | Infrastructure holds adapters, storage, locking, and observability implementations behind domain ports.          | 0.96       |
| EV-layers-composition-is-separate-di-root                     | Composition is a separate top-level DI root and assembly layer, not part of interfaces.                          | 0.97       |
| EV-layers-interfaces-are-driving-adapters                     | Interfaces are the driving-adapter edge and should route through application/composition seams.                  | 0.93       |
| EV-patterns-hexagonal-ports-and-adapters-is-explicit          | Hexagonal / Ports & Adapters is explicitly declared as the architecture style.                                   | 0.97       |
| EV-patterns-medallion-bronze-silver-gold-flow                 | Medallion data flow is explicit: Bronze -> Silver -> Gold, with Silver on Delta Lake.                            | 0.98       |
| EV-patterns-domain-driven-design-primitives                   | The domain layer explicitly uses DDD primitives such as ports, aggregates, value objects, entities, and schemas. | 0.94       |
| EV-patterns-dependency-injection-lives-in-composition         | Constructor injection and composition-root assembly are explicit architecture rules backed by tests.             | 0.97       |
| EV-patterns-registry-and-factory-assembly-seams               | Provider and pipeline assembly use explicit registry/factory seams in composition.                               | 0.91       |
| EV-enforcement-dependency-map-shows-zero-layer-violations     | The generated dependency map currently reports zero layer-policy violations.                                     | 0.97       |
| EV-enforcement-layer-dependency-suite-passes-baseline         | The layer-dependency architecture suite passes on the active baseline.                                           | 0.95       |
| EV-enforcement-bootstrap-and-composition-boundaries-pass      | Bootstrap/composition boundary suites pass on the active baseline.                                               | 0.94       |
| EV-enforcement-interface-and-adapter-di-guards-pass           | Interface and adapter DI guardrails pass on the active baseline.                                                 | 0.95       |
| EV-enforcement-import-matrix-is-docs-as-code                  | The import matrix is encoded in both active docs and executable architecture guardrails.                         | 0.93       |

## Evidence Gate Check

### layers-and-boundaries

- EV-layers-domain-pure-business-logic-no-io
- EV-layers-application-owns-orchestration-and-services
- EV-layers-infrastructure-hosts-adapters-storage-observability
- EV-layers-composition-is-separate-di-root
- EV-layers-interfaces-are-driving-adapters

Total: 5/5 minimum ✓ GATE PASSED

### architecture-patterns

- EV-patterns-hexagonal-ports-and-adapters-is-explicit
- EV-patterns-medallion-bronze-silver-gold-flow
- EV-patterns-domain-driven-design-primitives
- EV-patterns-dependency-injection-lives-in-composition
- EV-patterns-registry-and-factory-assembly-seams

Total: 5/5 minimum ✓ GATE PASSED

### enforcement-guardrails

- EV-enforcement-dependency-map-shows-zero-layer-violations
- EV-enforcement-layer-dependency-suite-passes-baseline
- EV-enforcement-bootstrap-and-composition-boundaries-pass
- EV-enforcement-interface-and-adapter-di-guards-pass
- EV-enforcement-import-matrix-is-docs-as-code

Total: 5/5 minimum ✓ GATE PASSED

## Ключевые выводы

- The repository still has a clear five-layer model, and the most important distinction is that `composition` remains a separate DI/assembly root rather than being folded into `interfaces`.
- The architectural style is not ambiguous: active docs repeatedly converge on Hexagonal Architecture, Medallion data flow, DDD-style domain modeling, and constructor-based DI.
- The current baseline is not held together only by prose. The generated dependency map reports zero layer-policy violations, and targeted architecture suites for layer dependencies, bootstrap/composition boundaries, and interface/DI guardrails all pass locally.
- The enforcement story is now fresher than in the initial pass: `RF-011` re-confirmed the same green baseline through a full verify refresh rather than a one-off architecture-only snapshot.

## Отмеченные противоречия

- ADR-005 documents that `interfaces -> infrastructure` is technically allowed in the import matrix, while the current `test_interfaces_no_infrastructure.py` suite encodes a stronger preferred practice for CLI-facing code. This is a tension in guidance scope, not a direct contradiction in the current baseline.
- The architecture style is strongly documented at the repo level, but individual provider pipelines may still expose transitional compatibility surfaces that are outside the scope of this pack.

## Оставшиеся пробелы

- This pack does not yet map every subpackage below the five top-level layers to a finer-grained responsibility inventory.
- It does not quantify how much of the codebase still relies on compatibility facades versus canonical public seams.
- It does not yet trace architecture ownership or churn by layer; it only establishes current structural and guardrail facts.
