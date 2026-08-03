# Consolidated Code Review — S1: Domain Layer

**Date:** 2026-07-16  
**Scope:** `src/bioetl/domain/`  
**Live size (`wc -l`):** 566 Python files, 74,717 LOC  
**Review mode:** L2 with two disjoint L3 reviews  
**Status:** PASS `[incomplete]`  
**Consolidated score:** 9.5/10.0  
**Qodo severity:** `UNSPECIFIED` for every loaded Qodo rule. The severities below are independent BioETL profile calibrations, not inferred Qodo severities.

## Findings first

| ID | BioETL severity | Finding | Primary evidence |
| --- | --- | --- | --- |
| S1-001 | HIGH | Normalization profile identity can vary between processes | `src/bioetl/domain/normalization/profiles/base.py:39`, `:49`, `:187`, `:271` |
| S1-002 | HIGH | `EffectiveConfigArtifact` is shallow-frozen; hashed semantic payload remains mutable | `src/bioetl/domain/control_plane/effective_config_artifact.py:80`, `:92`, `:113`, `:139`, `:168` |
| S1-003 | MEDIUM | Enforced domain complexity gate fails for two unregistered CC=7 functions | `src/bioetl/domain/exceptions/base.py:16`; `src/bioetl/domain/normalization/profiles/base.py:63` |
| S1-004 | MEDIUM | Missing deep-immutability regression coverage permits S1-002 to remain undetected | `tests/unit/domain/control_plane/test_effective_config_artifact.py:551` |

No verified CRITICAL findings were established.

### S1-001 — Normalization profile identity is process-dependent

- **BioETL severity:** HIGH — deterministic identity and exact-replay compatibility risk.
- **Rules:** `RULES.md` §4.3 and §6.1; `QG-DET-001`; Qodo IDs `718014`, `717993` with source severity `UNSPECIFIED`.
- **Evidence:** `_normalizer_ref()` returns `repr(normalizer)` for valid callable objects without instance-level `__module__` and `__qualname__` (`base.py:39-49`). It also canonicalizes closure cells through `_stable_value()`, whose fallback is `repr(value)` (`base.py:63-70`). These values enter `FieldRuleIdentity.compatibility_hash` (`base.py:187-200`) and `NormalizationProfileIdentity.profile_hash` (`base.py:271-295`).
- **Impact:** identical normalization code/config can publish different compatibility hashes across processes. Exact replay can then report false drift or reject a compatible run.
- **Dual verification:**
  1. Source trace: `_normalizer_ref()` / `_stable_value()` -> `FieldRule.identity` -> `NormalizationProfile.identity`.
  2. Fresh-process reproductions produced different hashes both for the same callable object and for a closure capturing the same set under different `PYTHONHASHSEED` values.
- **Valid-exception check:** this is not a documented dynamic `Any` boundary, test double, or graceful-degradation case. The public `Callable[..., object]` contract accepts the reproduced callable.
- **Verification commands:**

  ```bash
  for i in 1 2 3; do .venv/bin/python -c 'from bioetl.domain.normalization.profiles import FieldRule, NormalizationProfile; C=type("C",(),{"__call__":lambda self,value:value}); p=NormalizationProfile(profile_name="x",field_rules={"x":FieldRule("x",normalizer=C())}); print(p.field_identity("x").normalizer_ref,p.identity.profile_hash)'; done

  env PYTHONHASHSEED=1 .venv/bin/python -c "from bioetl.domain.normalization.profiles.base import FieldRule,NormalizationProfile; f=(lambda x:(lambda v:x and v))({'alpha','beta','gamma','delta','epsilon','zeta','eta','theta'}); print(NormalizationProfile('p',{'a':FieldRule('a',f)}).identity.profile_hash)"
  env PYTHONHASHSEED=2 .venv/bin/python -c "from bioetl.domain.normalization.profiles.base import FieldRule,NormalizationProfile; f=(lambda x:(lambda v:x and v))({'alpha','beta','gamma','delta','epsilon','zeta','eta','theta'}); print(NormalizationProfile('p',{'a':FieldRule('a',f)}).identity.profile_hash)"
  ```

- **Remediation direction:** require explicit stable identity for callable objects, or derive it from callable class identity plus canonical validated state. Reject unsupported state instead of hashing `repr()`.

### S1-002 — Effective config snapshots remain mutable after hashing

- **BioETL severity:** HIGH — reproducibility and control-plane evidence corruption risk.
- **Rules:** `QG-DET-001`; Qodo IDs `718014`, `717993` with source severity `UNSPECIFIED`; immutable effective-config/replay evidence contract.
- **Evidence:** frozen dataclasses retain mutable `JsonDict`, `dict`, and `list` fields directly: `ResolvedConfigSnapshot.config_data` (`effective_config_artifact.py:80-89`), `RuntimeOverrideSnapshot` (`:92-99`), `EffectiveExecutionConfig.config_data` (`:113-122`), and `EffectiveConfigArtifact.source_refs` plus policy collections (`:139-166`). `__post_init__()` (`:168-178`) validates strings/timestamps and sets a compatibility hash but performs no defensive copy or deep freeze.
- **Impact:** caller-owned config or artifact collections can be mutated after `resolved_config_hash`, `effective_config_hash`, `source_fingerprint`, and `artifact_id` are established. Persisted semantic data can therefore disagree with its identity anchors and weaken exact-replay/audit evidence.
- **Dual verification:**
  1. Source inspection confirms mutable aliases are stored unchanged across every frozen snapshot boundary.
  2. Runtime reproduction mutates the caller-owned config and appends to `source_refs`; both mutations remain visible through the frozen artifact.
- **Valid-exception check:** this is not a config-default exception. The finding concerns mutation after identity construction, not the presence of defaults.
- **Verification command:**

  ```bash
  .venv/bin/python -c 'from bioetl.domain.control_plane.effective_config_artifact import ConfigResolutionPolicy,EffectiveConfigArtifact,EffectiveExecutionConfig,ResolvedConfigSnapshot,RuntimeOverrideSnapshot; cfg={"mode":"safe"}; a=EffectiveConfigArtifact(artifact_id="a",pipeline_name="p",pipeline_kind="standard",source_refs=[],resolution_policy=ConfigResolutionPolicy(),resolved_config=ResolvedConfigSnapshot(config_type="standard",config_data=cfg,config_hash="h"),runtime_overrides=RuntimeOverrideSnapshot(),effective_execution_config=EffectiveExecutionConfig(config_data=cfg,effective_hash="eh"),resolved_config_hash="h",effective_config_hash="eh",source_fingerprint="f"); cfg["mode"]="mutated"; a.source_refs.append("not-a-ref"); print(a.resolved_config.config_data,a.source_refs)'
  ```

- **Remediation direction:** defensively copy and recursively freeze semantic payloads at construction boundaries; use immutable mappings/tuples and add nested/direct mutation tests.

### S1-003 — Domain complexity ratchet is failing

- **BioETL severity:** MEDIUM — enforced maintainability/testability gate failure with bounded runtime blast radius.
- **Rules:** `REQ-ARCH-010`; technical-debt budgets and exemptions MUST NOT increase.
- **Evidence:** the architecture gate reports `_redact()` at `src/bioetl/domain/exceptions/base.py:16` and `_stable_value()` at `src/bioetl/domain/normalization/profiles/base.py:63` as CC=7 against the domain maximum of 5. `configs/quality/architecture_metric_exemptions.yaml` has no `domain_complexity` entries.
- **Impact:** the current checkout fails an enforced architecture gate. `_stable_value()` is also on the deterministic identity path in S1-001; `_redact()` is on the structured error/security path.
- **Dual verification:**
  1. `TestDomainComplexity.test_cyclomatic_complexity_domain_layer` failed with both exact file/line entries.
  2. Independent Radon output reported `F 16:0 _redact - B (7)` and `F 63:0 _stable_value - B (7)`.
- **Working-tree attribution:** `_redact()` is part of a pre-existing/shared working-tree modification to `exceptions/base.py`; the review agents did not author it. `_stable_value()` was clean in the observed working tree.
- **Valid-exception check:** neither function has a registered exemption, and increasing the budget or adding an exemption merely to restore green status is prohibited.
- **Verification commands:**

  ```bash
  .venv/bin/python -m pytest -q tests/architecture/test_domain_purity.py::TestDomainComplexity::test_cyclomatic_complexity_domain_layer
  .venv/bin/radon cc -s src/bioetl/domain/exceptions/base.py src/bioetl/domain/normalization/profiles/base.py
  ```

- **Remediation direction:** decompose the value-family branches without relaxing the threshold or adding debt.

### S1-004 — Immutability tests cover reassignment, not nested mutation

- **BioETL severity:** MEDIUM — bounded regression-test gap on a replay-critical domain contract.
- **Rules:** `QG-TEST-001`; Qodo IDs `717831`, `717936` with source severity `UNSPECIFIED`.
- **Evidence:** `test_effective_config_artifact_immutability()` at `tests/unit/domain/control_plane/test_effective_config_artifact.py:551` asserts only that `artifact.artifact_id` cannot be reassigned. It does not exercise caller aliasing, nested `config_data` mutation, or mutation of list/dict fields.
- **Impact:** shallow frozen-dataclass behavior can regress while the documented immutability test remains green, allowing the S1-002 replay-evidence mismatch.
- **Dual verification:** source inspection of both the production dataclasses and the named test, plus the S1-002 runtime mutation reproduction.
- **Valid-exception check:** this is not a deterministic-test exception; the proposed regression is fully local and deterministic.
- **Verification command:**

  ```bash
  .venv/bin/python -m pytest -q tests/unit/domain/control_plane/test_effective_config_artifact.py
  ```

## Sub-review summary

| Sub-sector | Files | Reported LOC | Findings | Adjusted score | Status |
| --- | ---: | ---: | --- | ---: | --- |
| S1.1 — contracts, ports, schemas, types, exceptions, value objects, root | 259 | 30,795 | 1 MEDIUM after L2 gate reconciliation | 9.85 | PASS `[incomplete]` |
| S1.2 — domain logic, models, normalization, control plane, remaining packages | 307 | 43,943 | 2 HIGH, 1 MEDIUM plus 1 test-gap MEDIUM promoted at L2 | 9.20 | PASS `[incomplete]` |

The sub-review line counters count logical lines and total 74,738; the canonical live sector count above uses the profile-required `wc -l` result (74,717). File counts are disjoint and sum exactly to 566.

## Scoring

Worker scoring follows the profile: category score `max(0, 10 - deductions)`, with CRITICAL -2.0, HIGH -1.0, MEDIUM -0.5, LOW -0.25; category weights are Architecture 30%, Anti-Patterns 25%, DI 20%, Naming 10%, Types 10%, Testing 5%.

- S1.1 adjusted score: 9.85 (one MEDIUM in Architecture).
- S1.2 adjusted score: 9.20 (two HIGH plus one MEDIUM in Architecture; one MEDIUM in Testing).
- L2 file-weighted score: `(259 × 9.85 + 307 × 9.20) / 566 = 9.50`.

| Severity | Count |
| --- | ---: |
| CRITICAL | 0 |
| HIGH | 2 |
| MEDIUM | 2 |
| LOW | 0 |
| **Total** | **4** |

Profile thresholds: PASS >= 8.0, WARN 6.0-7.9, FAIL < 6.0. The PASS score reflects verified findings only and must be read with the `[incomplete]` coverage statement.

## Cross-zone checks and positive observations

- Full-tree AST/`rg` census covered all 566 Python files and found no domain imports from application, infrastructure, composition, or interfaces.
- No verified domain filesystem, network, HTTP, database, subprocess, `structlog`, hidden wall-clock, or random side effect was found.
- All cross-layer `*Port` protocols were `@runtime_checkable`; the undecorated `ClockLike` is a permitted layer-internal `*Protocol`, not an ARCH-003 violation.
- No missing public parameter/return annotations or non-exempt future-annotations omission was verified.
- Pandera/Pandas imports were confined to the ADR-048-sanctioned `domain/schemas/` and `domain/contracts/` representation boundaries.
- Internal imports among implementation modules beneath `domain.ports` were treated as facade construction/internal cohesion, not consumer imports that bypass `bioetl.domain.ports`.
- No hardcoded secret, credential, or production-looking token was verified in S1. Qodo security rules remained `UNSPECIFIED` and were not assigned invented severity.

## Validation executed

| Check | Outcome |
| --- | --- |
| Canonical memory `pre-task` workflow | PASS; retrieval non-degraded, no session-note write |
| Full S1 AST syntax/import/I/O/public-annotation/future/protocol census | PASS except promoted semantic findings above |
| Targeted architecture suite: domain purity/imports/I/O/ports/future/time/runtime-checkable/public API/Pandera/determinism | FAIL: the sole observed failure was the two-function domain complexity ratchet in S1-003; other selected checks completed without reported failure |
| Independent deterministic-hash subprocess reproductions | FAIL as expected; confirmed S1-001 |
| Independent shallow-mutation reproduction | FAIL as expected; confirmed S1-002 |
| Independent Radon check | FAIL as expected; confirmed both CC=7 entries in S1-003 |

## Coverage limitations

- `[incomplete]` Every scoped file was enumerated, parsed, and pattern-scanned, but a literal manual line-by-line semantic review of all 74,717 LOC was not completed under the bounded stop-loss.
- `[incomplete]` Manual deep review focused on deterministic normalization identity, effective-config/control-plane snapshots, ports/protocols, schemas/contracts, and generated candidates. Subtle behavior defects may remain in less deeply inspected behavior, entity, mapping, filtering, model, config, schema-field, and exception-taxonomy surfaces.
- `[incomplete]` The broader domain unit suite was stopped before a final result. Deferred command:

  ```bash
  .venv/bin/python -m pytest -q tests/unit/domain
  ```

- `[incomplete]` Some child architecture runs stalled on the mounted checkout; the consolidated targeted run produced the S1-003 failure, but this report does not claim a full `tests/architecture/` pass.
- Pre-existing/shared working-tree modifications were observed in:
  - `src/bioetl/domain/aggregates/_pipeline_run_mixins.py`
  - `src/bioetl/domain/behavior/_dq_serializer_html/_renderers.py`
  - `src/bioetl/domain/exceptions/base.py`
  - `src/bioetl/domain/models/_metadata_common.py`
  - `src/bioetl/domain/models/_metadata_gold.py`
  Review agents did not author these changes. Conclusions use the current checkout; S1-003 explicitly identifies the finding inside the modified exception file.

## Recommended order

1. Make normalization callable/state identity canonical and reject unsupported `repr()` fallbacks (S1-001).
2. Deep-freeze effective-config semantic payloads and cover caller-alias/nested mutation (S1-002, S1-004).
3. Refactor both CC=7 helpers without raising debt budgets or introducing exemptions (S1-003).

## Change and mirror status

- Production/test/config/docs changes by S1 review agents: none.
- Report artifacts created: `reports/review/S1.1-contracts-ports.md`, `reports/review/S1.2-logic-models.md`, `reports/review/S1-domain.md`.
- `.env` surfaces: not modified.
- Technical-debt outcome of the review itself: unchanged; no budget, threshold, exclusion, or exemption was increased.
- Runtime/docs mirror sync: not applicable; no runtime behavior or contributor guidance was changed.

