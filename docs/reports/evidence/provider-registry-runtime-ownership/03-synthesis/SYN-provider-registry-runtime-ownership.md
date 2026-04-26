# Synthesis: provider-registry-runtime-ownership

Rebaseline note: the current repo still supports stopping at the named runtime bootstrap seam; explicit runtime instance ownership remains unproven.

## Executive Summary

- The runtime/bootstrap area has already crossed the most important architectural threshold: raw class-level `ProviderRegistry.ensure_loaded()` access has been reduced behind a named composition seam. (`EV-provider-registry-runtime-bootstrap-now-flows-through-named-seam`)
- That seam is not merely cosmetic. Runtime tests now bind to it directly, and an architecture ratchet prevents the migrated runtime files from regressing back to raw class-level bootstrap access. (`EV-provider-registry-runtime-tests-now-bind-to-the-named-bootstrap-seam`, `EV-provider-registry-runtime-ratchet-already-prevents-raw-regression`)
- Explicit `ProviderRegistry` instance threading clearly pays off in datasource and nearby factory seams, where provider lookup and creator resolution are already locally owned concerns. (`EV-provider-registry-explicit-instance-threading-already-pays-off-in-local-factory-seams`)
- The current runtime/bootstrap callers do not yet present the same ownership shape. They explicitly manage pipeline-registry lifecycle and bootstrap ordering, but they do not naturally own a `ProviderRegistry` instance. (`EV-provider-registry-runtime-callers-do-not-yet-own-provider-instance-lifecycle`)
- The active RF-07 governance plan still treats explicit runtime instance ownership as a later analysis question, not as a required continuation of the current wave. (`EV-provider-registry-governance-still-defers-runtime-instance-ownership-decision`)

## Key Insights

### Insight 1: The main runtime risk has already been reduced from hidden class-level access to an explicit bootstrap seam

**Observation:** The four deferred runtime files now use `ensure_providers_loaded()` or `ensure_providers_loaded_fn` instead of raw `ProviderRegistry.ensure_loaded()` calls.
**Implication:** The original runtime problem was primarily a hidden dependency seam. That specific problem has been materially reduced already, even without explicit `ProviderRegistry` instance ownership.
**Confidence:** 0.96
**Evidence:** `EV-provider-registry-runtime-bootstrap-now-flows-through-named-seam`

### Insight 2: The new seam is now operationally real because tests and ratchets are aligned with it

**Observation:** Runtime tests patch or inject the named seam directly, and `test_registry_contracts.py` now blocks regression to raw class-level bootstrap in the migrated runtime files.
**Implication:** The named seam is no longer just an internal cleanup detail; it has become part of the enforceable runtime contract. This sharply reduces the urgency of pushing farther into explicit instance threading without stronger evidence.
**Confidence:** 0.95
**Evidence:** `EV-provider-registry-runtime-tests-now-bind-to-the-named-bootstrap-seam`, `EV-provider-registry-runtime-ratchet-already-prevents-raw-regression`

### Insight 3: Explicit registry ownership is a good pattern, but only where ownership is already local

**Observation:** In datasource and adjacent pipeline-factory seams, explicit `provider_registry` threading now works well because those code paths already own provider lookup, config resolution, and creator construction.
**Implication:** The evidence supports explicit instance ownership as a selective pattern, not yet as a universal migration target. The pattern has clear value in local factory seams, but that does not automatically transfer to runtime/bootstrap orchestration.
**Confidence:** 0.95
**Evidence:** `EV-provider-registry-explicit-instance-threading-already-pays-off-in-local-factory-seams`

### Insight 4: Runtime/bootstrap still lacks a strong natural owner for a ProviderRegistry instance

**Observation:** Runtime signatures expose `PipelineRegistry`, registry factories, and bootstrap callables, but not an obvious caller that should own and thread a `ProviderRegistry` instance.
**Implication:** Forcing explicit runtime registry ownership now would risk adding new plumbing without a correspondingly clear gain in locality, reasoning, or test isolation. The current seam may already be the right stopping point for this wave.
**Confidence:** 0.91
**Evidence:** `EV-provider-registry-runtime-callers-do-not-yet-own-provider-instance-lifecycle`

### Insight 5: Governance intent still favors stopping after seam stabilization unless stronger evidence appears

**Observation:** The active RF-07 plan explicitly separates “make bootstrap explicit” from “decide whether runtime should own a registry instance.”
**Implication:** The current project policy already assumes that explicit runtime instance ownership is optional and should be justified later, not pursued automatically. This aligns with the current code and test evidence rather than contradicting it.
**Confidence:** 0.86
**Evidence:** `EV-provider-registry-governance-still-defers-runtime-instance-ownership-decision`

## Contradictions and Resolutions

### Tension 1: Explicit instance threading is successful elsewhere, so should runtime adopt it too?

**Evidence in tension**

- `EV-provider-registry-explicit-instance-threading-already-pays-off-in-local-factory-seams`
- `EV-provider-registry-runtime-callers-do-not-yet-own-provider-instance-lifecycle`

**Resolution:** This is a scope mismatch, not a true conflict. Explicit instance threading is strongly supported in seams that already own provider-bound construction work. Runtime/bootstrap currently owns coordination and ordering, not provider-registry lifecycle. The pattern is valid, but the ownership boundary is not yet equivalent.

### Tension 2: If the default registry compatibility layer still exists, has the runtime problem really been solved?

**Evidence in tension**

- `EV-provider-registry-runtime-bootstrap-now-flows-through-named-seam`
- `EV-provider-registry-runtime-ratchet-already-prevents-raw-regression`

**Resolution:** The problem has been reduced at the runtime boundary even though the compatibility layer still exists globally. RF-07 was never framed as “delete the default registry.” The current successful outcome is narrower: make runtime/bootstrap dependencies visible and prevent new hidden class-level access in the migrated scope.

## Gaps and Uncertainties

- We still do not have a concrete runtime caller that naturally creates, owns, and benefits from threading an isolated `ProviderRegistry` instance.
- The current evidence is strong about seam visibility and regression control, but weaker about the long-term testing or operational benefits of explicit runtime ownership.
- There is not yet a demonstrated runtime scenario, fixture, or multi-registry execution mode that is blocked by the current named bootstrap seam.
- Because the compatibility layer remains intentionally alive, future contributors may still overgeneralize the datasource pattern unless runtime ownership guidance is documented clearly in the next decision layer.

## Recommended Next Step

- Treat the current named runtime bootstrap seam as the sufficient RF-07D stopping point for now.
- Do **not** start a second runtime migration wave toward explicit `ProviderRegistry` instance ownership unless a new caller-driven case appears.
- If a later case does appear, require evidence of at least one of the following before reopening RF-07D4:
  - a runtime path that already owns an isolated registry naturally;
  - a testability or isolation problem that the current seam cannot solve;
  - a real need to run multiple runtime/bootstrap registry contexts in parallel or independently.

## Top Insights

1. The major runtime dependency problem has already been reduced to a visible, injectable seam. (`EV-provider-registry-runtime-bootstrap-now-flows-through-named-seam`)
1. Tests and architecture guards now make that seam enforceable, not just descriptive. (`EV-provider-registry-runtime-tests-now-bind-to-the-named-bootstrap-seam`, `EV-provider-registry-runtime-ratchet-already-prevents-raw-regression`)
1. Explicit `ProviderRegistry` instance ownership is currently a strong local-factory pattern, not yet a justified runtime/bootstrap pattern. (`EV-provider-registry-explicit-instance-threading-already-pays-off-in-local-factory-seams`, `EV-provider-registry-runtime-callers-do-not-yet-own-provider-instance-lifecycle`)
