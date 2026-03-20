# Pipeline Config Loader Ownership Decision Summary

## Accepted Decision

- retain `PipelineConfigLoader` as a legacy infrastructure convenience seam
- do not treat `PipelineConfigLoader` as the canonical owner of the pipeline
  config flow

## Decision

For the current `RF-FS-004` wave, `PipelineConfigLoader` should stay in place,
but only as a retained convenience surface for DQ-aware infrastructure usage.
Canonical ownership should remain centered on:

- `src/bioetl/infrastructure/config/pipeline_config_api.py` for staged YAML
  loading
- `src/bioetl/infrastructure/config/domain_config_resolver.py` for YAML + DQ ->
  domain resolution
- narrower helpers such as
  `src/bioetl/infrastructure/config/pipeline_dq_resolution.py` for extracted DQ
  behavior

## Why

- the canonical loading flow has already moved to `pipeline_config_api.py`
- the canonical domain bridge has already moved to `domain_config_resolver.py`
- higher-layer contracts already model loading and mapping as separate seams
- the class still has direct tested value as a convenience and cache-control
  surface

## Reopen Criteria

Reopen this decision only if:

- `PipelineConfigLoader` loses its remaining integration value, or
- the remaining convenience methods can be replaced cleanly by narrower
  canonical APIs without increasing call-site complexity.
