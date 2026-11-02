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
- **E1 NORMATIVE**: ADR-005 (Composition Root / wiring isolation) — `docs/02-architecture/decisions/ADR-005-composition-layer-separation.md` (composition stays separate from `interfaces/`; only Composition Root knows concrete infrastructure assembly). ADR-058 covers layered **protocol placement** (`domain` / `application` / `composition/contracts`), not Composition Root ownership — do not use it as the primary normative basis for this audit.
- **E2 STATIC**: `src/bioetl/composition/entrypoints.py:35` (Primary composition root facades and exports mapped exactly to scorecard allowed 12 methods)
- **E2 STATIC**: `src/bioetl/composition/_service_registry.py:44` (`typed_port` and `_LazyServiceFactory` thunks ensuring determinism and explicit protocol binding)
- **E2 STATIC**: `src/bioetl/composition/factories/pipeline/registry_core.py:41` (Core pipeline registration via `PipelineDefinition` strict struct)
- **E2 STATIC**: `src/bioetl/composition/providers/provider_registry.py:69-79,90-99,107-142,145-195` (`ProviderRegistry` instance `threading.RLock` covers store mutations and configuration lookup only; `create_adapter` / `create_data_source` call `ProviderCreator` **after** the lock is released, so creation callbacks are not serialized by that RLock)
- **E2 STATIC**: `src/bioetl/composition/bootstrap/cli/config.py:36` (CLI `bootstrap_config_service` wiring `get_settings`, `PipelineConfigLoaderPort`, etc. explicitly)
- **E3 EXECUTABLE**: `uv run pytest tests/architecture/ -k composition` — scope=`tests/architecture/`, checkout_sha=`f2fdceaac024d3bcd0f90f87e0e03553965a00df` (**≠** Pinned Revision `a5243cb4bbed67b267daecdc097b8c48501e140a`; tip adds audit report + inventory + honesty edits only — `git diff --stat a5243cb4..f2fdceaac0 -- src/bioetl/composition/` empty), UTC start=`2026-11-02T20:25:07Z`, UTC end=`2026-11-02T20:25:57Z`, exit_code=`0`, output=`110 passed, 5635 deselected in 48.77s`. Broader filter `-k "composition or wiring or port"` is **not** bound as success: same tip produced exit_code=`1` with 8 failures in unrelated governance/coverage audits.

## D. Findings Register
*(No actionable deficiencies found against ADR-005 Composition Root isolation and the static wiring surfaces listed above within audited scope. Thread-safety is not claimed beyond `ProviderRegistry` store/lookup RLock — see H.)*

## E. Quantitative Scorecard
- `src/bioetl/composition/`: 5 (Mature implementation + automated enforcement + sufficient current evidence/tests)
- The architecture features a clean separation between entrypoints and factories, strict deterministic registrations, robust composition-focused architecture tests (`-k composition`, E3), and well-defined lifetime boundaries (thunks are cleanly bound via `_service_registry.py`).

## F. Cross-cutting/root-cause clusters
- None.

## G. Prioritized roadmap P0→P3
- N/A. Everything conforms to rules in scope.

## H. Verification Matrix
- **Composition Root**: Verified against ADR-005 within audited scope (`src/bioetl/composition/**` + `bootstrap/factories/registry`, line 6). No hidden Composition Root was found **in that scope**. `entrypoints.py` acts as the strict external boundary for the audited tree; exhaustive repo-wide search outside scope was not claimed.
- **Builder/factory chains**: Verified within audited scope. Checked across CLI pipeline, workflows, tests, and maintenance commands that consume composition entrypoints.
- **Runtime registration determinism**: Verified. No side effects upon import (`_LazyServiceFactory` defers execution).
- **Scope/lifetime matrix**: Verified for lazy thunks / explicit factories. **Thread-safety:** `ProviderRegistry` `RLock` protects instance store mutations and configuration lookup only; `create_adapter` / `create_data_source` invoke `ProviderCreator` after the lock is released. `_service_registry._REGISTRY` has no lock; `get_default_provider_registry()` lazy singleton creation (`providers/_default_registry.py:90-98`) is not synchronized. Do not generalize "registries are thread-safe".
- **State leakage**: Verified. Tests clearly mock out registries, and registries implement `clear()` methods specific for tests.
- **Workflow/composite wiring**: Verified. `runner_factory_builder_service.py` uses correct pipelines factories.

## I. `NOT_VERIFIABLE` and missing evidence
- Cross-process / multi-threaded contention on `_service_registry`, default-provider singleton creation, and `ProviderCreator` callbacks after RLock release: not exercised here → remains **NOT_VERIFIABLE** (not scored as a defect without a failing concurrent case).
- Hidden Composition Roots outside audited scope (line 6): **NOT_VERIFIABLE** / not claimed.

## J. Self-check
- Attempted disproof: Looked for hardcoded dependencies in `application` and `domain`. Found none. Checked file sizes and explicit mappings. Re-checked normative cite (ADR-005 vs ADR-058), E3 checkout SHA vs Pinned Revision, Composition Root claim scope, and `ProviderRegistry` RLock vs post-lock creation callbacks.
- Exception handling verified for scoped claims.
- Score is consistent with evidence after honesty corrections.

## K. Verdict
The Composition Root (per ADR-005) correctly owns concrete wiring and DI assembly **within audited scope**. Runtime registration for covered factories is deterministic and lacks side effects on import. `ProviderRegistry` store operations and configuration lookup are RLock-guarded, while creation callbacks run after the lock is released; service-registry dict and default-registry singleton creation are **not** covered by that claim. No violations observed in the audited static + `-k composition` executable scope (checkout `f2fdceaac0` ≠ pinned `a5243cb4`, composition sources unchanged). Score remains 5 for DI/composition maturity within those bounds.
