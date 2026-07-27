# Sunset design: `bioetl.infrastructure.config` package-root compatibility debt

**Status:** design approved for execution window  
**Owner:** `@bioetl-config`  
**Linked issues:** #6624 (TD-08), parent #6628  
**Reviewed on:** 2026-07-27  
**Deprecation start:** 2026-07-27  
**External sunset target:** 2026-10-21 (aligns with public-API quarterly review)  
**Hard removal candidate:** first minor after 2026-10-21 only with owner ack

## Problem

Among public lazy facades, exactly one surface remains classified as
`compatibility_debt`:

| Field | Value |
| --- | --- |
| Module | `bioetl.infrastructure.config` |
| Path | `src/bioetl/infrastructure/config/__init__.py` |
| Markers | `__getattr__` lazy re-exports + historical package-root re-exports |
| Classification | `compatibility_debt` |
| Allowed importers | `external_compatibility_consumers`, `tests` |
| First-party `src` importers | **must remain 0** |

Transition/sunset/expired compatibility metrics are already `0/0/0`. This facade
is residual package-root convenience debt for external consumers, not an active
twin-module pair.

## Canonical owner import paths

External and first-party code **SHOULD** import owner modules directly:

| Symbol / capability | Canonical import |
| --- | --- |
| `Settings`, `get_settings`, `PipelineSettings`, `ObservabilitySettings` | `bioetl.infrastructure.config._base` (or settings API surface used by composition) |
| `get_pipeline_config`, `yaml_config_to_domain` | `bioetl.infrastructure.config._base` |
| `PipelineConfigLoader` | `bioetl.infrastructure.config.pipeline_config_loader` |
| `load_pipeline_config` | `bioetl.infrastructure.config.pipeline_config_api` |
| `load_composite_config` | `bioetl.infrastructure.config.composite_config_api` |
| `load_workflow_config` | `bioetl.infrastructure.config.workflow_config_api` |
| `load_source_config` | `bioetl.infrastructure.config.source_config_loader` |
| `DQConfigLoader` | `bioetl.infrastructure.config.dq_config_loader` |
| `FilterConfigLoader` | `bioetl.infrastructure.config.filter_config_loader` |
| `BaseConfigLoader` | `bioetl.infrastructure.config.base_config_loader` |
| Contract policy loader | `bioetl.infrastructure.config.contract_policy_loader` |

Composition Root and application services **MUST NOT** grow first-party imports
of the package root for convenience.

## Deprecation notice (external)

Package-root imports such as:

```python
from bioetl.infrastructure.config import Settings, load_pipeline_config
```

are **deprecated** for new external code as of 2026-07-27. Prefer the canonical
owner paths in the table above. Existing external consumers may keep using the
package root until the sunset target; behavior remains identical during the
window.

## Enforcement during the window

1. `configs/quality/public_lazy_facade_inventory.yaml` keeps
   `classification: compatibility_debt` until removal or permanent-public
   reclassification with architecture approval.
2. `configs/quality/internal_compatibility_shim_inventory.yaml` entry
   `infrastructure-config-package-root` keeps `max_src_importer_count: 0`.
3. Compatibility importer census `--check` remains green with zero first-party
   `src` importers of the package root.
4. No new transition_compat / twin_pair growth is allowed to “hide” this sunset.

## Exit criteria

Any one of the following, with owner approval:

1. **Remove:** collapse lazy `__getattr__` re-exports and drop
   `compatibility_debt` after external BC window and zero first-party `src`
   importers (preferred).
2. **Reclassify permanent public:** only with explicit architecture review that
   the package root is a sanctioned public API seam (then update inventories;
   do not label it dead code).
3. **Defer with dated review:** if external consumers are still unknown, keep
   `compatibility_debt` but refresh `review_by` without raising transition
   metrics.

## Non-goals

- Do not introduce twin modules or transition shims.
- Do not raise debt budgets / transition counts to buy time.
- Do not re-label permanent CLI/composition entrypoints as removable dead code.

## Verification commands

```bash
python -m scripts.engineering.qa report-compatibility-importer-census --check
python -m scripts.engineering.qa report-debt-governance-gates --check
```

## Decision log

| Date | Decision |
| --- | --- |
| 2026-07-27 | Publish sunset design (TD-08). Keep facade as `compatibility_debt` during external window; first-party `src` importers stay 0. |
