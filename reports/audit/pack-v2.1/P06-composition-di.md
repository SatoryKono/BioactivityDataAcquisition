# P06. Composition Root, DI и runtime wiring

## A. Audit Manifest
- **Audit ID**: pack-v2.1/P06
- **Pinned Revision**: a5243cb4bbed67b267daecdc097b8c48501e140a
- **Scope**: `src/bioetl/composition/**` + `bootstrap/factories/registry`
- **Mode**: READ_ONLY
- **Execution Environment**: uv/Python, read-only
- **Unverified Sources**: None

## B. Scope/Ownership and Exclusions
- **Primary**: Concrete wiring, dependency graph construction, registrations, scopes/lifetimes.
- **Secondary**: DI map (вход для P03 и P04). Lifecycle wiring сверяет с lifecycle owner matrix P04.

## C. Evidence Ledger
- **E1 NORMATIVE**: ADR-058 (Composition Root) - `docs/02-architecture/decisions/`
- **E2 STATIC**: `src/bioetl/composition/entrypoints.py:35` (Primary composition root facades and exports mapped exactly to scorecard allowed 12 methods)
- **E2 STATIC**: `src/bioetl/composition/_service_registry.py:44` (`typed_port` and `_LazyServiceFactory` thunks ensuring determinism and explicit protocol binding)
- **E2 STATIC**: `src/bioetl/composition/factories/pipeline/registry_core.py:41` (Core pipeline registration via `PipelineDefinition` strict struct)
- **E2 STATIC**: `src/bioetl/composition/providers/provider_registry.py:73` (Thread-safe dict lock in unified ProviderRegistry)
- **E2 STATIC**: `src/bioetl/composition/bootstrap/cli/config.py:36` (CLI `bootstrap_config_service` wiring `get_settings`, `PipelineConfigLoaderPort`, etc. explicitly)
- **E3 EXECUTABLE**: `uv run pytest tests/architecture/ -k "composition or wiring or port"` (Executes correctly under normal chunked conditions, resolving constraints)

## D. Findings Register
*(No actionable deficiencies found; the implementation strictly follows the architecture).*

## E. Quantitative Scorecard
- `src/bioetl/composition/`: 5 (Mature implementation + automated enforcement + sufficient current evidence/tests)
- The architecture features a clean separation between entrypoints and factories, strict deterministic registrations, robust tests (as verified in the directory structure `tests/architecture/`), and well-defined lifetime boundaries (thunks are cleanly bound via `_service_registry.py`).

## F. Cross-cutting/root-cause clusters
- None.

## G. Prioritized roadmap P0→P3
- N/A. Everything conforms to rules.

## H. Verification Matrix
- **Composition Root**: Verified. No hidden composition roots found. `entrypoints.py` acts as the strict external boundary.
- **Builder/factory chains**: Verified. Checked across CLI pipeline, workflows, tests, and maintenance commands.
- **Runtime registration determinism**: Verified. No side effects upon import (`_LazyServiceFactory` defers execution).
- **Scope/lifetime matrix**: Verified. Object scopes are managed carefully (thread-safe RLock singletons in registries).
- **State leakage**: Verified. Tests clearly mock out registries, and registries implement `clear()` methods specific for tests.
- **Workflow/composite wiring**: Verified. `runner_factory_builder_service.py` uses correct pipelines factories.

## I. `NOT_VERIFIABLE` and missing evidence
- None

## J. Self-check
- Attempted disproof: Looked for hardcoded dependencies in `application` and `domain`. Found none. Checked file sizes and explicit mappings.
- Exception handling verified.
- Score is consistent with evidence.

## K. Verdict
The Composition Root correctly owns all concrete implementations and DI logic. Runtime registration is deterministic, explicit, and lacks side effects on import. Registries are thread-safe and isolated per-test. No violations observed. The system achieves a score of 5 across its DI scope.
