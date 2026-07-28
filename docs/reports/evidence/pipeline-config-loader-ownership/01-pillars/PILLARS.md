# Pipeline Config Loader Ownership

## Research Question

After the current `RF-FS-004` slices, should `PipelineConfigLoader` remain a
legacy convenience owner, or should canonical ownership be tightened further
around `pipeline_config_api.py` and `domain_config_resolver.py`?

## Scope

- canonical pipeline YAML loading flow in
  `src/bioetl/infrastructure/config/pipeline_config_api.py`
- canonical YAML + DQ -> domain bridge in
  `src/bioetl/infrastructure/config/domain_config_resolver.py`
- convenience bridge in `src/bioetl/infrastructure/config/_base.py`
- remaining `PipelineConfigLoader` responsibilities in
  `src/bioetl/infrastructure/config/pipeline_config_loader.py`
- extracted DQ helper logic in
  `src/bioetl/infrastructure/config/pipeline_dq_resolution.py`
- application and domain contracts that expose config loading seams
- integration tests that still bind directly to `PipelineConfigLoader`
- active `RF-FS-004` plan language for this hotspot

## Out Of Scope

- deleting `PipelineConfigLoader` outright
- redesigning DQ hierarchy semantics
- changing YAML corpus shape
- broader `RF-FS-004` ownership cleanup outside the loader decision

## Evaluation Focus

1. Where does canonical staged YAML loading live now?
1. Where does canonical YAML + DQ -> domain resolution live now?
1. Do higher layers still treat `PipelineConfigLoader` as the primary contract?
1. What concrete value does `PipelineConfigLoader` still provide?
1. Does current code support retaining the class only as a legacy convenience
   seam rather than as a behavioral owner?
