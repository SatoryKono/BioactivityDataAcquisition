# Synthesis: pipeline-config-loader-ownership

Rebaseline note: the current repo still supports the retain-and-thin reading for `PipelineConfigLoader`; canonical ownership remains in the narrower API/resolver seams.

## Executive Summary

- Canonical staged YAML loading now lives in
  `pipeline_config_api.py`, not in `PipelineConfigLoader`.
  (`EV-pipeline-config-api-now-owns-staged-yaml-loading`)
- Canonical YAML + DQ -> domain resolution now lives in
  `domain_config_resolver.py`, and `get_pipeline_config()` already uses that
  bridge as the top-level convenience path.
  (`EV-domain-config-resolver-now-owns-yaml-plus-dq-domain-bridge`)
- Higher-layer architecture still treats loading and mapping as separate seams,
  which argues against restoring `PipelineConfigLoader` as the main config
  contract. (`EV-higher-layers-model-loading-and-mapping-as-separate-seams`)
- `PipelineConfigLoader` is still a live, tested infrastructure convenience
  surface for DQ-aware loading and cache clearing, so deleting it now would be
  premature. (`EV-pipeline-config-loader-still-provides-tested-convenience-surface`)
- The recent extraction to `pipeline_dq_resolution.py` shows the right direction:
  keep thinning the class while moving canonical behavior into narrower helper
  modules. (`EV-dq-resolution-extraction-shows-loader-can-thin-without-owning-logic`)

## Key Insights

### Insight 1: Canonical ownership has already moved away from the class

**Observation:** `pipeline_config_api.py` explicitly owns the staged
`read -> normalize -> validate -> map` flow, and `domain_config_resolver.py`
explicitly owns the YAML + DQ -> domain bridge.
**Implication:** Treating `PipelineConfigLoader` as the canonical owner would now
fight the actual architecture that has already been established.
**Confidence:** 0.97
**Evidence:** `EV-pipeline-config-api-now-owns-staged-yaml-loading`,
`EV-domain-config-resolver-now-owns-yaml-plus-dq-domain-bridge`

### Insight 2: The class still has real retained value, but that value is local

**Observation:** Integration tests still exercise `PipelineConfigLoader`
directly for `load_pipeline_config()`, `resolve_dq_config()`, and
`clear_cache()`.
**Implication:** The class should not be deleted in this wave. Its current value
is as a local infrastructure convenience seam, not as the main topology owner.
**Confidence:** 0.95
**Evidence:** `EV-pipeline-config-loader-still-provides-tested-convenience-surface`

### Insight 3: The correct next move is to retain and thin, not to re-center

**Observation:** DQ helper behavior has already been extracted into
`pipeline_dq_resolution.py`, and the active RF-FS-004 plan still flags the
loader as a mixed hotspot rather than a settled owner.
**Implication:** The safest interpretation is to keep `PipelineConfigLoader`
available while continuing to tighten ownership around function-based canonical
modules.
**Confidence:** 0.93
**Evidence:** `EV-dq-resolution-extraction-shows-loader-can-thin-without-owning-logic`,
`EV-rf-fs-004-governance-still-treats-loader-as-mixed-hotspot`

## Contradictions and Resolutions

### Tension 1: If the class is still tested directly, should it remain the owner?

**Evidence in tension**

- `EV-pipeline-config-loader-still-provides-tested-convenience-surface`
- `EV-pipeline-config-api-now-owns-staged-yaml-loading`
- `EV-domain-config-resolver-now-owns-yaml-plus-dq-domain-bridge`

**Resolution:** This is not a true contradiction. The class is still useful, but
its usefulness is now local and convenience-oriented. The canonical end-to-end
ownership has already moved to narrower modules.

### Tension 2: Would removing the class simplify the topology further?

**Evidence in tension**

- `EV-higher-layers-model-loading-and-mapping-as-separate-seams`
- `EV-pipeline-config-loader-still-provides-tested-convenience-surface`

**Resolution:** Probably yes eventually, but current evidence does not yet
support immediate deletion. The class still carries a tested convenience seam
for DQ-aware infrastructure workflows and cache clearing. The better near-term
move is to retain it while preventing ownership drift.

## Recommended Interpretation Boundary

- Keep `PipelineConfigLoader`, but treat it as a retained infrastructure
  convenience seam.
- Do not treat it as the canonical owner of pipeline YAML loading or
  YAML + DQ -> domain resolution.
- Continue moving detailed behavior into `pipeline_config_api.py`,
  `domain_config_resolver.py`, and narrower helper modules such as
  `pipeline_dq_resolution.py`.

## Reopen Criteria

Revisit this decision only if at least one of these becomes true:

- no production or test paths still benefit from the class-level convenience
  surface;
- cache-clearing and injected DQ/filter convenience can be expressed cleanly
  through smaller canonical APIs;
- a later `RF-FS-004` slice proves that the remaining class adds only indirection
  and no meaningful isolation value.
