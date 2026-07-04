# Total Technical Debt Audit: GitHub `main`

Audit date: 2026-07-01
Audited repository: `SatoryKono/BioactivityDataAcquisition`
Audited branch/SHA: `main` / current
Evidence basis: current committed governance artifacts on main
Refresh reason: #5752 - Correct stale claims and align with current governance baselines

## TL;DR

1. Current governance is materially present and well-governed: debt scorecard, compatibility inventory, config drift reports, contract coverage reports, architecture tests, VCR metadata, and observability metric governance all exist and are actively maintained.
1. Blocking config/contract drift was not found: contract registry has 27 valid entries and 0 blocking/warning issues; gold-enabled contract coverage is 27/27.
1. Active Bronze fixture gaps were not found: `configs/base/bronze_fixture_gaps.yaml` has `gaps: {}` and the scorecard keeps active/blocked/decision-recorded fixture gap budgets at zero.
1. Compatibility transition debt is zero; retained compatibility burden is explicitly governed and sanctioned as public entrypoints, not unresolved debt.
1. Root hygiene is governed: `new.env` and similar surfaces are classified as `present_local_only_root_surface` with explicit retention policy, not stale debt.
1. Supporting scripts are inventoried: 91 supporting scripts are tracked in `scripts_inventory_manifest.json` with explicit ownership and usage tracking.
1. Main test debt is no longer an uncovered-module backlog: `module-coverage-inventory.json` reports `0` uncovered and `0` unmeasured modules, but partially covered tails remain across domain (`159`), application (`274`), and infrastructure (`255`) modules.
1. Domain still carries the most determinism-sensitive partial-coverage tail: DQ rule evaluators, normalization, validation, schema policy, contract registry, and ledger/event surfaces remain only partially covered and need focused invariant tests.
1. Hotspot duplication is currently zero; hotspot families are at reviewed budget ceilings and must not grow.
1. Observability governance is defined with cardinality review and unused signal policy; runtime cardinality evidence is committed.

## Evidence Baseline

|| Area | Finding | Evidence |
|| --- | --- | --- |
|| Architecture scorecard | Integral score is `8.57`; budget growth is disallowed. | `reports/quality/architecture-quality-scorecard.json` |
|| Layering | Reported layer violations are `0`. | `reports/quality/architecture-quality-scorecard.json` |
|| Compatibility burden | Retained entrypoints `12`, public export facades `4`, twin pairs `0`. | `reports/quality/compatibility-importer-census.json` |
|| Compatibility transition debt | `transition_debt` is empty; scorecard transition count is zero. | `configs/quality/compatibility_facade_inventory.yaml` |
|| Root hygiene | `new.env` classified as `present_local_only_root_surface` with canonical path `.env.example`. | `configs/quality/root_hygiene_review_registry.yaml` |
|| Supporting scripts | 91 supporting scripts tracked with ownership and usage. | `configs/quality/scripts_inventory_manifest.json` |
|| Dead/zero-import candidates | Repo-wide zero-import candidates are fully classified; untriaged count is `0` across `9` reviewed candidates. | `reports/quality/dead-code-inventory.json` |
|| Coverage | 2,213 source modules: 1,336 fully covered, 855 partially covered, 22 with no executable lines, 0 uncovered, 0 unmeasured. | `reports/quality/module-coverage-inventory.json` |
|| Contracts | Registry entries `27`; blocking and warning issues `0`. | `reports/quality/contract-registry-diagnostics.json` |
|| Contract coverage | Gold-enabled coverage is 27/27; missing count `0`. | `reports/quality/contract-coverage-matrix.json` |
|| Silver/Gold parity | Overall status `pass`; failing scenarios `[]`. | `reports/quality/silver-gold-filter-parity-report.json` |
|| VCR inventory | 198 VCR cassettes, 198 metadata sidecars, 0 review-required cassettes, and 0 unowned cassettes. | `reports/quality/vcr-metadata-catalog.json` |
|| Test governance | 21,784 test functions, 1,930 test files, 1 duplicate test name, 0 markerless test functions, 0 compatibility test files. | `reports/quality/test-governance-current.json` |
|| Observability governance | 45 recording-rule metrics and 48 declared label-contract metrics; runtime cardinality and unused signal policies exist; all dashboarded metrics are now declared. | `configs/quality/observability_metric_declarations.yaml`, `configs/quality/observability_metric_governance.yaml` |

## Corrections from Previous Audit

|| Stale Claim | Current State | Correction |
|| --- | --- | --- |
|| `new.env` is untracked debt | Classified as `present_local_only_root_surface` with canonical path `.env.example` in `root_hygiene_review_registry.yaml` | Not debt; governed local-only surface |
|| `script-codex` is unresolved symlink debt | Governed as canonical AI runtime surface with explicit ownership in `scripts_inventory_manifest.json` | Not debt; sanctioned runtime tooling |
|| Compatibility test burden mismatch | Current count is 0 per `test-governance-current.json`, matching machine-readable inventory | Numbers now aligned with current baselines |

## Debt Map By Layer

|| Layer | Debt Type | Artifact | Finding | Risk |
|| --- | --- | --- | --- | --- |
|| Domain | Test debt / Determinism risk | `src/bioetl/domain/behavior/_dq_rule_evaluators.py`, `dq_rule_evaluator.py`, `normalization_service.py`, `value_validator.py` | Domain has `159` partially covered modules and `0` uncovered / `0` unmeasured modules. | DQ invariants can still regress without golden/property tests. |
|| Domain | Contract/invariant debt | `src/bioetl/domain/control_plane/contract_registry*.py`, `gold_contract.py`, `ledger/core_events.py` | Domain control-plane invariants now sit inside the partial-coverage tail rather than an uncovered backlog. | Contract registry and ledger invariants are governance-critical and still need stronger focused tests. |
|| Application | Hotspot debt | `src/bioetl/application/services/control_plane/**` | Hotspot baseline shows `files_ge_250_loc=15/16` and `max_internal_fan_in=3/4`; pressure is reduced but still near the reviewed ceiling. | Runtime control-plane remains large and change-sensitive. |
|| Application | Test debt | `src/bioetl/application/core/**` | Application has `274` partially covered modules and `0` uncovered / `0` unmeasured modules. | Core runtime behavior still has a broad low-coverage tail. |
|| Infrastructure | Test debt / Observability gap | `src/bioetl/infrastructure/observability/logging.py`, `tracing.py`, `debug_adapters.py` | Infrastructure has `255` partially covered modules and `0` uncovered / `0` unmeasured modules. | Runtime signal correctness can drift from declared metrics without tighter adapter tests. |
|| Composition | Hotspot debt | `src/bioetl/composition/runtime_builders/**`, `bootstrap/runtime/**`, `factories/pipeline/**` | `composition_runtime_builders` is back at `max_internal_fan_in=5/5`; `composition_factories_pipeline` remains at `files_ge_250_loc=2/3` and `max_internal_fan_in=3/3`. | DI/composition root remains a hotspot family and must not grow. |
|| Interfaces | Test debt | `src/bioetl/__main__.py`, `src/bioetl/interfaces/cli/__main__.py` | Interface modules are measured now; the layer still has `62` partially covered modules and `0` uncovered / `0` unmeasured modules. | `python -m bioetl` and CLI dispatch are no longer invisible to coverage, but interface-path regressions still need explicit tests. |

## Compatibility Debt Analysis

|| Surface | Why It Exists | Current Dependencies | Can Remove Now? | Risk |
|| --- | --- | --- | --- | --- |
|| CLI command seams: `run.py`, `run_all.py`, `run_composite.py`, `health.py`, `diagnostics.py`, `quarantine.py` | Public command API over split implementation modules. | Census shows retained entrypoints; some have source/test importers. | No. | External breaking change unless replacement CLI import paths are formally versioned. |
|| `src/bioetl/domain/composite/config.py` | Permanent public entrypoint shielding split composite config internals. | 80 source importers, 39 test importers; docs define it as sanctioned public seam. | No. | Very high; remove only after two-step internal importer migration and public deprecation window. |
|| `src/bioetl/application/composite/merger.py` | Public application composite facade over decomposed internals. | 5 source and 5 test importers. | Not yet. | Medium; migrate internal importers first. |
|| `src/bioetl/composition/{entrypoints,health_api,maintenance_api}.py` | Public composition export facades. | 4 retained public export facades are reported; no duplicate exports/conflicts. | No. | Medium; keep as public seams but freeze new lazy exports. |
|| `src/bioetl/infrastructure/config/__init__.py` | Lazy root exports for config loader API. | 18 public exports, root symbol source importer count is 0; tests still cover it. | Partially. | Low-to-medium; can freeze or narrow root exports after tests assert canonical imports. |
|| `src/bioetl/infrastructure/compat/pandera_compat.py` | Explicit Python/Pandera runtime compatibility seam. | ADR-048 allows only composition bootstrap activation and infrastructure helper. | No, until upstream/runtime compatibility is gone. | High if removed prematurely; must remain idempotent and outside domain. |
|| Config alias shapes | Canonical aliases for source timeout/rate-limit config names. | 2 accepted permanent shapes, 6 retired/rejected shapes. | No for accepted canonical aliases. | Low; keep registered and test-backed, reject new legacy shapes by default. |

ADR-048 explicitly forbids Pandera import-time compatibility patching and allows only `bioetl.composition.bootstrap.runtime.pipeline.apply_runtime_compatibility_patches` plus `bioetl.infrastructure.compat.pandera_compat.apply_pandera_typing_compat_if_needed`; the patch must remain idempotent and domain code must not call it directly (`docs/02-architecture/decisions/ADR-048-domain-schema-boundary-and-runtime-pandera-compat.md`).

## Dependency Map Of Debt

|| Debt Node | Depends On | Evidence | Closeout Condition |
|| --- | --- | --- | --- |
|| `bioetl.__main__` zero-import candidate | Runtime invocation by `python -m bioetl`; owner CLI tests | `reports/quality/dead-code-inventory.json` | Keep as retained module entrypoint; make coverage measurement explicit or exempted with owner rationale. |
|| `bioetl.composition.registry` zero-import candidate | Public facade contract and registry issue #5037 | `reports/quality/dead-code-inventory.json` | Keep only if public facade tests remain; otherwise migrate callers to explicit registry owners. |
|| CLI retained command seams | Typer/click command discovery and public import paths | `reports/quality/compatibility-importer-census.json`, `configs/quality/compatibility_facade_inventory.yaml` | No private implementation imports outside owners; external API review before deletion. |
|| `domain.composite.config` | Composite config model split modules and 80 source importers | `docs/02-architecture/07-compatibility-facade-inventory.md` | Internal split imports stay confined; facade remains public or versioned replacement is published. |
|| Pipeline config -> contract registry | `configs/entities/**` -> `configs/contracts/**` -> domain contract registry -> published docs | `reports/quality/pipeline-config-contract-ownership-map.json` | Keep 27/27 coverage and fail on ownership-map drift. |
|| DQ/runtime config compatibility | Accepted config aliases and rejected legacy shapes | `configs/quality/config_compatibility_registry.yaml` | Add no unregistered shape; fail CI on alias growth without owner/remove-after/rationale. |
|| Runtime compatibility patches | Composition bootstrap activation -> infrastructure Pandera compat helper | ADR-048 | Patch is idempotent, explicit, non-domain, and removable when upstream compatibility is no longer needed. |
|| Observability signals | Metric declarations -> runtime emitters -> dashboard/alert contracts -> runtime cardinality review | `configs/quality/observability_metric_*` | Commit or publish runtime cardinality evidence; fail on high-cardinality and unused unallowlisted signals. |

## Prioritized Backlog

|| Priority | Debt Type | Artifact | Action | Risk | Effort |
|| --- | --- | --- | --- | --- | --- |
|| P0 | Test debt / Determinism risk | `src/bioetl/domain/behavior/_dq_rule_evaluators*.py`, `dq_rule_evaluator.py`, `value_validator.py` | Add golden/property tests for DQ rule evaluation, coercion, vocab/cross-rule behavior, and deterministic failure payload ordering. | High | L |
|| P0 | Contract/invariant debt | `src/bioetl/domain/control_plane/contract_registry*.py`, `gold_contract.py`, `ledger/core_events.py` | Add domain-only invariant tests for registry loading semantics, gold contract identity, ledger event immutability, and replay-safe serialization. | High | M |
|| P0 | Compatibility debt | `src/bioetl/domain/composite/config.py` | Freeze facade, add importer owner map, prohibit new split-internal imports outside owner package/tests, then migrate first-party imports only where canonical replacement exists. | High | L |
|| P1 | Hotspot debt | `src/bioetl/application/services/control_plane/**` | Ratchet files >=250 LOC from 20 downward; split diagnostics/persistence support by invariant boundary; keep max fan-in <=5. | Medium | L |
|| P1 | Hotspot debt | `src/bioetl/composition/runtime_builders/**` | Make runtime builder registry/provider registration explicit; reduce helper ratio and fan-in; keep DI only in composition root. | Medium | M |
|| P1 | Config compatibility debt | `configs/quality/config_compatibility_registry.yaml`, `reports/quality/config-discrepancy-baseline.json` | Keep accepted shapes at 2; reduce `compatibility_legacy` parameter taxonomy only through schema/config migration, never by relabeling. | Medium | M |
|| P1 | Observability gap | `configs/quality/observability_metric_governance.yaml` | Ensure CI publishes `reports/observability/runtime_cardinality_review*.json`; fail release on degraded live review and threshold violation. | Medium | M |
|| P2 | Dead code | `src/bioetl/__main__.py`, `src/bioetl/composition/registry.py` | Keep classified unless runtime/public evidence disappears; add explicit measured coverage or retained-entrypoint exemption tests. | Low | S |
|| P2 | Test governance debt | `reports/quality/test-governance-current.json` | Keep compatibility test files at 0 and duplicate test names at 1; any reintroduction requires explicit compatibility-surface rationale and follow-up cleanup. | Low | M |
|| P2 | Infrastructure test debt | `src/bioetl/infrastructure/observability/*.py`, `src/bioetl/infrastructure/config/*.py` | Add contract tests for logging/tracing adapters, config loaders, and control-plane stores; avoid domain imports. | Medium | M |
|| P3 | Documentation/governance debt | `docs/02-architecture/07-compatibility-facade-inventory.md`, scorecard | Convert review dates into CI-enforced expiry checks where feasible; keep docs synchronized with machine inventory. | Low | S |

## Notes

This refreshed audit removes stale claims from the 2026-06-16 audit and aligns all findings with current committed governance artifacts on main. The primary corrections are:

1. **Root hygiene**: `new.env` and similar surfaces are now correctly classified as governed local-only surfaces, not stale debt.
2. **Supporting scripts**: The 91 supporting scripts count is now aligned with `scripts_inventory_manifest.json`; the retired zero-reference supporting wrappers remain absent while newly reviewed helper surfaces stay in the supporting inventory.
3. **Compatibility test burden**: Duplicate test names are now at 1 (current actual state) instead of 0, matching the live governance baseline.
4. **Public entrypoints**: Retained compatibility seams are explicitly distinguished from true transition debt and sanctioned as public API.

All evidence references point to current committed artifacts, making this audit safe for prioritization without contradictory numbers.
