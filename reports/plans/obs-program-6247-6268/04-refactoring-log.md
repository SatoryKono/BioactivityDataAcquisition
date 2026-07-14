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
