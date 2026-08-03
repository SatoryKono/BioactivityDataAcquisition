# Refactoring Log: obs-program-6247-6268

**Date**: 2026-07-14
**Scope**: bounded observability closure campaign debugging

## DBG-001 — cached Bronze root scope

- **Symptom**: isolated campaign attempts read the first globally sorted cached
  Bronze file instead of the requested ChEMBL entity.
- **Root cause**: the cached-reader wiring treated a provider-wide Bronze root as
  an already entity-scoped directory.
- **Change**: scope provider/entity roots in observability wiring while preserving
  backwards compatibility for explicitly entity-scoped cache paths.
- **Evidence**: focused composition tests and successful runtime probes for the
  previously cross-contaminated activity, assay, assay-parameter, and cell-line
  attempts.

## DBG-002 — target-component description normalization

- **Symptom**: `chembl_target_component` stopped with a strict normalization
  contract error for `description`.
- **Root cause**: the transformer and accepted Gold contract use `description`,
  while the Pandera/config/pseudo-null surfaces still used the stale
  `component_description` name.
- **Change**: align the runtime schema, entity config, and normalization registry
  on `description`, with a regression test for the explicit pseudo-null rule.
- **Debt outcome**: normalization fallback is removed; no threshold or debt budget
  changed.

## DBG-003 — target classification ID/schema drift

- **Symptom**: `chembl_target_protein_classification` passed DQ and then failed
  Arrow conversion because numeric classification IDs were emitted as strings.
- **Root cause**: the Arrow writer declared numeric hierarchy IDs even though the
  governed Silver schema deliberately preserves external IDs as strings; the
  Arrow schema also omitted newer relation/provenance fields.
- **Change**: retain string IDs and synchronize the Arrow schema with the accepted
  Silver relation surface.
- **Debt outcome**: schema drift decreases; no contract relaxation or budget
  increase is introduced.

## DBG-004 — workflow fixture compatibility

- **Symptom**: campaign preflight could not find workflow records in a canonical
  compressed Bronze cache; independent CI samples also had no shared
  assay-to-target-to-publication keys.
- **Root cause**: staging searched only `*.jsonl` and assumed independently
  sampled entity fixtures were naturally join-compatible.
- **Change**: stream both JSONL and Zstandard JSONL inputs, preserve lossless
  compatible joins when available, and otherwise record an explicit deterministic
  join projection with separate source-record and staged-record SHA-256 values.
- **Debt outcome**: workflow evidence becomes reproducible and provenance-bound;
  no DQ threshold or debt budget changes.

## DBG-005 — registry discovery checkout isolation

- **Symptom**: the network-capable campaign stalled before creating its audit root
  while the nested `bioetl config list-pipelines` command resolved an ambient
  editable environment.
- **Root cause**: registry discovery did not receive the explicit checkout
  `PYTHONPATH` used by isolated pipeline attempts.
- **Change**: bind registry discovery to the campaign checkout's `src` and root
  paths through its subprocess environment.
- **Debt outcome**: campaign provenance becomes independent of ambient editable
  installs; no runtime configuration or budget changes.
