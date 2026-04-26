# Pipeline Config Loader Ownership Evidence Summary

Review note (2026-03-27): included in the repo-wide evidence-pack sweep; see `docs/reports/evidence/project-evidence-rebaseline/06-status/EVIDENCE-PACK-REVIEW-2026-03-27.md` for wave status, retained-vs-reopened interpretation, and current review scope.

Примечание о rebaseline: the current repo state still supports the retain-and-thin interpretation for `PipelineConfigLoader`; canonical ownership remains with the narrower resolver/API seams.

## Question

After the current `RF-FS-004` slices, should `PipelineConfigLoader` remain a
legacy convenience owner, or should canonical ownership be tightened further
around `pipeline_config_api.py` and `domain_config_resolver.py`?

## Evidence Collected

- `EV-pipeline-config-api-now-owns-staged-yaml-loading`
- `EV-domain-config-resolver-now-owns-yaml-plus-dq-domain-bridge`
- `EV-higher-layers-model-loading-and-mapping-as-separate-seams`
- `EV-pipeline-config-loader-still-provides-tested-convenience-surface`
- `EV-dq-resolution-extraction-shows-loader-can-thin-without-owning-logic`
- `EV-rf-fs-004-governance-still-treats-loader-as-mixed-hotspot`

## What The Evidence Currently Supports

1. Canonical staged pipeline YAML loading now lives in
   `pipeline_config_api.py`.
1. Canonical YAML + DQ -> domain resolution now lives in
   `domain_config_resolver.py`.
1. `PipelineConfigLoader` is no longer the architectural center of the config
   topology.
1. `PipelineConfigLoader` still adds real retained value as a tested
   infrastructure convenience seam.

## Текущая интерпретация Boundary

This evidence pack supports a conservative interpretation:

- keep `PipelineConfigLoader` for now;
- do not treat it as the canonical owner anymore;
- continue thinning it while holding canonical ownership in
  `pipeline_config_api.py`, `domain_config_resolver.py`, and narrower helper
  modules.

## Remaining Gap

What is still missing is a later slice proving whether the remaining
convenience methods should ultimately stay as a sanctioned shim or collapse into
smaller explicit APIs. The current evidence is strong enough to reject
re-centering the class, but not yet strong enough to justify deletion.

## Риски

- Formal risk tracking now lives in [05-risks/RISKS.yaml](./05-risks/RISKS.yaml).
