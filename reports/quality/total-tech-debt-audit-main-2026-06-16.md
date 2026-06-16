# Total Technical Debt Audit: GitHub `main`

Audit date: 2026-06-16
Audited repository: `SatoryKono/BioactivityDataAcquisition`
Audited branch/SHA: `main` / `0426564c258cabfaaf0c4dc321d657f570a57c98`
Evidence basis: clean GitHub archive snapshot, not the dirty local working tree.

## TL;DR

1. Current governance is materially present: debt scorecard, compatibility inventory, config drift reports, contract coverage reports, architecture tests, VCR metadata, and observability metric governance all exist.
1. Blocking config/contract drift was not found in the audited snapshot: contract registry has 27 valid entries and 0 blocking/warning issues; gold-enabled contract coverage is 27/27.
1. Active Bronze fixture gaps were not found: `configs/base/bronze_fixture_gaps.yaml` has `gaps: {}` and the scorecard keeps active/blocked/decision-recorded fixture gap budgets at zero.
1. Compatibility transition debt is zero, but retained compatibility/API burden is still significant: 14 retained public entrypoints, 4 retained public export facades, and 1 lazy-export twin pair.
1. The highest-risk compatibility seam is `src/bioetl/domain/composite/config.py`: it is sanctioned, but has 80 source importers and 39 test importers, so removal is not a near-term action.
1. Main test debt is not duplicate tests or flaky evidence; it is coverage/invariant debt: 125 source modules are uncovered and 2 CLI entry modules are unmeasured.
1. Domain has the most serious coverage debt: 57 uncovered modules, including DQ rule evaluators, normalization, validation, schema policy, contract registry, and ledger/event surfaces.
1. Hotspot duplication is currently zero, but several hotspot families sit at reviewed budget ceilings or near them, especially `application_services_control_plane`, `composition_runtime_builders`, `composition_factories_pipeline`, and `application_core`.
1. Observability governance is defined, including cardinality review and unused signal policy, but the audit did not find a committed runtime cardinality evidence artifact in the inspected quality reports. Treat live observability evidence as `[incomplete]`.
1. The deterministic debt reduction plan should be ratchet-only: isolate retained compatibility seams, migrate internal imports to canonical owners, remove only zero-import/non-public residues, then enforce no-growth budgets in CI.

## Evidence Baseline

| Area | Finding | Evidence |
| --- | --- | --- |
| Architecture scorecard | Integral score is `7.98`; budget growth is disallowed. | `reports/quality/architecture-quality-scorecard.json:32`, `:159` |
| Layering | Reported layer violations are `0`. | `reports/quality/architecture-quality-scorecard.json:42`, `:146` |
| Compatibility burden | Retained entrypoints `14`, public export facades `4`, twin pairs `1`. | `reports/quality/compatibility-importer-census.json:7`, `:12`, `:18` |
| Compatibility transition debt | `transition_debt` is empty; scorecard transition count is zero. | `configs/quality/compatibility_facade_inventory.yaml`, `configs/quality/debt_scorecard.yaml:93` |
| Dead/zero-import candidates | Repo-wide zero-import candidates are fully classified; count is `2`. | `reports/quality/dead-code-inventory.json:18` |
| Coverage | 2,137 source modules: 823 fully covered, 1,187 partially covered, 125 uncovered, 2 unmeasured. | `reports/quality/module-coverage-inventory.json` |
| Contracts | Registry entries `27`; blocking and warning issues `0`. | `reports/quality/contract-registry-diagnostics.json:3`, `:6`, `:7` |
| Contract coverage | Gold-enabled coverage is 27/27; missing count `0`. | `reports/quality/contract-coverage-matrix.json:2`, `:6` |
| Silver/Gold parity | Overall status `pass`; failing scenarios `[]`. | `reports/quality/silver-gold-filter-parity-report.json:4`, `:105` |
| VCR inventory | 205 VCR cassettes, all with `managed_inventory`; active fixture gaps are empty. | `reports/quality/vcr-metadata-catalog.json`, `configs/base/bronze_fixture_gaps.yaml:3` |
| Test governance | 20,608 test functions, 1,760 test files, 0 duplicate test names, 0 markerless test functions, 32 compatibility test files. | `reports/quality/test-governance-current.json` |
| Observability governance | 29 recording-rule metrics and 48 declared label-contract metrics; runtime cardinality and unused signal policies exist. | `configs/quality/observability_metric_declarations.yaml:3`, `:33`; `configs/quality/observability_metric_governance.yaml:20`, `:75` |

## Debt Map By Layer

| Layer | Debt Type | Artifact | Finding | Risk |
| --- | --- | --- | --- | --- |
| Domain | Test debt / Determinism risk | `src/bioetl/domain/behavior/_dq_rule_evaluators.py`, `dq_rule_evaluator.py`, `normalization_service.py`, `value_validator.py` | Domain behavior has uncovered modules; total domain uncovered count is 57. | DQ invariants can regress without golden/property tests. |
| Domain | Compatibility debt | `src/bioetl/domain/composite/config.py` | Sanctioned public entrypoint with 80 source and 39 test importers. | High removal risk; collapse requires import migration and facade contract tests. |
| Domain | Contract/invariant debt | `src/bioetl/domain/control_plane/contract_registry*.py`, `gold_contract.py`, `ledger/core_events.py` | These domain control-plane modules are uncovered in `main`. | Contract registry and ledger invariants are governance-critical but weakly covered. |
| Application | Hotspot debt | `src/bioetl/application/services/control_plane/**` | 100 files, 14,894 LOC, 20 files >=250 LOC, max fan-in 5, helper ratio 0.499. | Runtime control-plane is decomposed but still large and near budget. |
| Application | Compatibility debt | `src/bioetl/application/composite/merger.py`, checkpoint compatibility services | Retained application seams and checkpoint compatibility helpers still exist. | Resume/replay safety depends on compatibility logic remaining explicit and tested. |
| Application | Test debt | `src/bioetl/application/core/**` | 176 modules, 6 uncovered, 132 below 85%; covered line percent 48.09 in hotspot summary. | Core runtime behavior has broad low-coverage tail. |
| Infrastructure | Compatibility debt | `src/bioetl/infrastructure/config/__init__.py`, `src/bioetl/infrastructure/compat/pandera_compat.py`, storage writer facades | Lazy config root exports and runtime third-party compatibility seam remain. | Allowed only while explicitly owned; import-time patching must not leak into domain. |
| Infrastructure | Test debt / Observability gap | `src/bioetl/infrastructure/observability/logging.py`, `tracing.py`, `debug_adapters.py` | Infrastructure has 61 uncovered modules; observability runtime modules appear in uncovered set. | Runtime signal correctness can drift from declared metrics. |
| Composition | Compatibility debt | `src/bioetl/composition/entrypoints.py`, `health_api.py`, `maintenance_api.py`, `lazy_exports.py` | 4 retained public export facades and 1 lazy-export twin pair. | Public API protection is explicit, but lazy indirection increases import-surface complexity. |
| Composition | Hotspot debt | `src/bioetl/composition/runtime_builders/**`, `bootstrap/runtime/**`, `factories/pipeline/**` | Runtime builders helper ratio 0.502 and fan-in 9; factories pipeline has 4 files >=250 LOC at budget. | DI/composition root remains a hotspot family and must not grow. |
| Interfaces | Compatibility debt | `src/bioetl/interfaces/cli/commands/*.py` | CLI command modules are retained public seams over split domain command owners. | Removal is external breaking change; internal imports must stay on canonical command seams. |
| Interfaces | Test debt | `src/bioetl/__main__.py`, `src/bioetl/interfaces/cli/__main__.py` | Both are unmeasured in coverage inventory. | `python -m bioetl` and CLI module dispatch are owner-tested but not coverage-measured. |

## Compatibility Debt Analysis

| Surface | Why It Exists | Current Dependencies | Can Remove Now? | Risk |
| --- | --- | --- | --- | --- |
| CLI command seams: `run.py`, `run_all.py`, `run_composite.py`, `health.py`, `diagnostics.py`, `quarantine.py`, `maintenance.py` | Public command API over split implementation modules. | Census shows retained entrypoints; some have source/test importers. | No. | External breaking change unless replacement CLI import paths are formally versioned. |
| `src/bioetl/domain/composite/config.py` | Permanent public entrypoint shielding split composite config internals. | 80 source importers, 39 test importers; docs define it as sanctioned public seam. | No. | Very high; remove only after two-step internal importer migration and public deprecation window. |
| `src/bioetl/domain/value_objects/activity_values.py` | Public value-object facade shielding split activity value modules. | Retained entrypoint with owner tests. | No. | Medium; collapse only if public API contract changes are acceptable. |
| `src/bioetl/application/composite/merger.py` | Public application composite facade over decomposed internals. | 5 source and 5 test importers. | Not yet. | Medium; migrate internal importers first. |
| `src/bioetl/composition/{entrypoints,health_api,maintenance_api}.py` | Public composition export facades. | 4 retained public export facades are reported; no duplicate exports/conflicts. | No. | Medium; keep as public seams but freeze new lazy exports. |
| `src/bioetl/composition/lazy_exports.py` and `_lazy_exports.py` | Public/private lazy-export twin pair. | Public module has source importers; private module is imported by public wrapper. | No. | Medium; target is to eliminate private direct importers, then reassess twin. |
| `src/bioetl/infrastructure/config/__init__.py` | Lazy root exports for config loader API. | 18 public exports, root symbol source importer count is 0; tests still cover it. | Partially. | Low-to-medium; can freeze or narrow root exports after tests assert canonical imports. |
| `src/bioetl/infrastructure/compat/pandera_compat.py` | Explicit Python/Pandera runtime compatibility seam. | ADR-048 allows only composition bootstrap activation and infrastructure helper. | No, until upstream/runtime compatibility is gone. | High if removed prematurely; must remain idempotent and outside domain. |
| Config alias shapes | Canonical aliases for source timeout/rate-limit config names. | 2 accepted permanent shapes, 6 retired/rejected shapes. | No for accepted canonical aliases. | Low; keep registered and test-backed, reject new legacy shapes by default. |

ADR-048 explicitly forbids Pandera import-time compatibility patching and allows only `bioetl.composition.bootstrap.runtime.pipeline.apply_runtime_compatibility_patches` plus `bioetl.infrastructure.compat.pandera_compat.apply_pandera_typing_compat_if_needed`; the patch must remain idempotent and domain code must not call it directly (`docs/02-architecture/decisions/ADR-048-domain-schema-boundary-and-runtime-pandera-compat.md:63`, `:69`, `:73`, `:86`, `:101`).

## Dependency Map Of Debt

| Debt Node | Depends On | Evidence | Closeout Condition |
| --- | --- | --- | --- |
| `bioetl.__main__` zero-import candidate | Runtime invocation by `python -m bioetl`; owner CLI tests | `reports/quality/dead-code-inventory.json` | Keep as retained module entrypoint; make coverage measurement explicit or exempted with owner rationale. |
| `bioetl.composition.registry` zero-import candidate | Public facade contract and registry issue #5037 | `reports/quality/dead-code-inventory.json` | Keep only if public facade tests remain; otherwise migrate callers to explicit registry owners. |
| CLI retained command seams | Typer/click command discovery and public import paths | `reports/quality/compatibility-importer-census.json`, `configs/quality/compatibility_facade_inventory.yaml` | No private implementation imports outside owners; external API review before deletion. |
| `domain.composite.config` | Composite config model split modules and 80 source importers | `docs/02-architecture/07-compatibility-facade-inventory.md:155` | Internal split imports stay confined; facade remains public or versioned replacement is published. |
| Pipeline config -> contract registry | `configs/entities/**` -> `configs/contracts/**` -> domain contract registry -> published docs | `reports/quality/pipeline-config-contract-ownership-map.json` | Keep 27/27 coverage and fail on ownership-map drift. |
| DQ/runtime config compatibility | Accepted config aliases and rejected legacy shapes | `configs/quality/config_compatibility_registry.yaml` | Add no unregistered shape; fail CI on alias growth without owner/remove-after/rationale. |
| Runtime compatibility patches | Composition bootstrap activation -> infrastructure Pandera compat helper | ADR-048 | Patch is idempotent, explicit, non-domain, and removable when upstream compatibility is no longer needed. |
| Observability signals | Metric declarations -> runtime emitters -> dashboard/alert contracts -> runtime cardinality review | `configs/quality/observability_metric_*` | Commit or publish runtime cardinality evidence; fail on high-cardinality and unused unallowlisted signals. |

## Prioritized Backlog

| Priority | Debt Type | Artifact | Action | Risk | Effort |
| --- | --- | --- | --- | --- | --- |
| P0 | Test debt / Determinism risk | `src/bioetl/domain/behavior/_dq_rule_evaluators*.py`, `dq_rule_evaluator.py`, `value_validator.py` | Add golden/property tests for DQ rule evaluation, coercion, vocab/cross-rule behavior, and deterministic failure payload ordering. | High | L |
| P0 | Contract/invariant debt | `src/bioetl/domain/control_plane/contract_registry*.py`, `gold_contract.py`, `ledger/core_events.py` | Add domain-only invariant tests for registry loading semantics, gold contract identity, ledger event immutability, and replay-safe serialization. | High | M |
| P0 | Compatibility debt | `src/bioetl/domain/composite/config.py` | Freeze facade, add importer owner map, prohibit new split-internal imports outside owner package/tests, then migrate first-party imports only where canonical replacement exists. | High | L |
| P1 | Hotspot debt | `src/bioetl/application/services/control_plane/**` | Ratchet files >=250 LOC from 20 downward; split diagnostics/persistence support by invariant boundary; keep max fan-in <=5. | Medium | L |
| P1 | Hotspot debt | `src/bioetl/composition/runtime_builders/**` | Make runtime builder registry/provider registration explicit; reduce helper ratio and fan-in; keep DI only in composition root. | Medium | M |
| P1 | Compatibility debt | `src/bioetl/composition/lazy_exports.py`, `_lazy_exports.py` | Remove private direct importers; turn lazy table into explicit public export map with tests for no orphan/conflict exports. | Medium | M |
| P1 | Config compatibility debt | `configs/quality/config_compatibility_registry.yaml`, `reports/quality/config-discrepancy-baseline.json` | Keep accepted shapes at 2; reduce `compatibility_legacy` parameter taxonomy only through schema/config migration, never by relabeling. | Medium | M |
| P1 | Observability gap | `configs/quality/observability_metric_governance.yaml` | Ensure CI publishes `reports/observability/runtime_cardinality_review*.json`; fail release on degraded live review and threshold violation. | Medium | M |
| P2 | Dead code | `src/bioetl/__main__.py`, `src/bioetl/composition/registry.py` | Keep classified unless runtime/public evidence disappears; add explicit measured coverage or retained-entrypoint exemption tests. | Low | S |
| P2 | Test governance debt | `reports/quality/test-governance-current.json` | Burn down compatibility test files below 32 only after deleting corresponding compatibility surfaces; keep duplicate names at zero. | Low | M |
| P2 | Infrastructure test debt | `src/bioetl/infrastructure/observability/*.py`, `src/bioetl/infrastructure/config/*.py` | Add contract tests for logging/tracing adapters, config loaders, and control-plane stores; avoid domain imports. | Medium | M |
| P3 | Documentation/governance debt | `docs/02-architecture/07-compatibility-facade-inventory.md`, scorecard | Convert review dates into CI-enforced expiry checks where feasible; keep docs synchronized with machine inventory. | Low | S |

## Roadmap

### Phase 1 - Visibility

| Priority | Debt Type | Artifact | Action | Risk | Effort |
| --- | --- | --- | --- | --- | --- |
| P0 | Test debt | `reports/quality/module-coverage-inventory.json` | Produce layer-scoped uncovered/low-coverage debt slices and owner each domain/control-plane module. | Low | S |
| P0 | Compatibility debt | `reports/quality/compatibility-importer-census.json` | Generate dependency map for all 14 retained entrypoints and 4 export facades. | Low | S |
| P1 | Observability gap | `configs/quality/observability_metric_governance.yaml` | Add committed/release artifact check for runtime cardinality review availability. | Medium | M |
| P1 | Hotspot debt | `reports/quality/hotspot-family-baseline.json` | Add trend gates for helper ratio and files >=250 LOC, not only duplicate clusters. | Low | S |

### Phase 2 - Isolation

| Priority | Debt Type | Artifact | Action | Risk | Effort |
| --- | --- | --- | --- | --- | --- |
| P0 | Compatibility debt | CLI/domain/composition facades | Freeze new internal imports through architecture tests; route all new code to canonical owners. | Medium | M |
| P0 | Architectural violation prevention | `tests/architecture/test_layer_dependencies.py`, `test_forbidden_imports.py` | Keep domain free of I/O, Pandera compat patching, and infrastructure imports; fail fast on new violations. | Medium | S |
| P1 | Runtime/CLI split debt | `src/bioetl/interfaces/cli/commands/**`, `src/bioetl/composition/bootstrap/runtime/**` | Keep CLI as adapter only; move reusable runtime assembly behind composition services, not CLI modules. | Medium | M |
| P1 | Contract drift prevention | `pipeline-config-contract-ownership-map.json` | Require every new entity config to have contract, code owner, registry source, and published artifact row. | Low | S |

### Phase 3 - Removal

| Priority | Debt Type | Artifact | Action | Risk | Effort |
| --- | --- | --- | --- | --- | --- |
| P0 | Dead code | Zero-import candidates | Delete only when runtime/public entrypoint evidence is gone and owner tests are migrated. | Medium | S |
| P0 | Compatibility debt | Retained facades with zero first-party importers | Remove or convert to external-only entrypoint after deprecation policy; never remove `domain.composite.config` first. | High | L |
| P1 | Duplication/hotspot debt | Control-plane and runtime builder families | Continue decomposing large files under 250 LOC and reduce fan-in budgets after each clean baseline. | Medium | L |
| P1 | Config debt | Compatibility legacy parameters | Migrate legacy config keys to canonical schemas and update fixtures/contracts; reject new aliases by default. | Medium | M |

### Phase 4 - Enforcement

| Priority | Debt Type | Artifact | Action | Risk | Effort |
| --- | --- | --- | --- | --- | --- |
| P0 | Governance | `configs/quality/debt_scorecard.yaml` | Keep no-growth/downward-only budgets; fail on any increase in compatibility, hotspot, config drift, VCR gap, or dead-code untriaged counts. | Low | S |
| P0 | Architecture | `tests/architecture/**` | Make strict layering, import graph, composition root, Pandera seam, and domain purity tests blocking in CI. | Medium | S |
| P1 | Test debt | Coverage inventory | Add fail-fast gates for domain/control-plane uncovered module count and ratchet toward zero. | Medium | M |
| P1 | Observability | Metric governance | Fail on high-cardinality labels, emitted-without-contract events, unused declared metrics without allowlist, and degraded release cardinality review. | Medium | M |

## Enforcement Strategy

- Keep existing architecture tests as required CI gates: layer dependencies, forbidden imports, import graph invariants, private imports, composition factory boundaries, config/contract drift, compatibility census, VCR metadata, deterministic identity, replay time seams, and observability metric governance.
- Add a layer-specific coverage ratchet: fail if domain uncovered modules exceed the current baseline of 57, then ratchet down after each cleanup.
- Add a compatibility importer ratchet: fail if retained public entrypoints exceed 14, public export facades exceed 4, or lazy twin pairs exceed 1.
- Add a hotspot budget ratchet: fail on any growth in files >=250 LOC, max internal fan-in, helper ratio, or duplicate clusters for the five hotspot families.
- Add a config compatibility ratchet: accepted config compatibility shapes must stay at 2; rejected/retired shapes must not be reintroduced.
- Add observability fail-fast: declared metrics require label contracts and runtime evidence; release gates must fail on high-cardinality threshold violation or degraded live review.
- Add contract ownership fail-fast: every new `configs/entities/**` row must map to a contract, registry source, code owner, and published artifact.
- Add deterministic/replay fail-fast for new time/UUID/random seams unless registered in existing runtime seam inventories.

## Risks And Trade-offs

- Removing retained public entrypoints too aggressively will break external users and tests; first reduce first-party dependencies, then run a deprecation window.
- `domain.composite.config` is compatibility debt but also the sanctioned public API; collapsing it prematurely is higher risk than keeping it frozen.
- Coverage ratchets can create false progress if tests only import modules; require invariant/golden/property assertions, especially for DQ and control-plane domain logic.
- Observability enforcement must distinguish local PR fallback from release evidence; allowing fallback in release gates would hide production cardinality drift.
- Config compatibility cleanup should migrate schemas/contracts, not simply rename taxonomy labels from `compatibility_legacy` to another category.
- Hotspot budgets must only ratchet downward or stay flat. Increasing budgets would violate project guardrails and hide structural debt.

## Incomplete Areas

- `[incomplete]` Runtime cardinality evidence artifact was not found in the inspected committed quality reports; governance policy exists, but live evidence must be verified in CI artifacts.
- `[incomplete]` Flaky test evidence was not derivable from static repository artifacts alone; no CI run history was audited in this report.
- `[incomplete]` External consumer impact for public entrypoint removal requires release/package telemetry or downstream import analysis outside this repository snapshot.

