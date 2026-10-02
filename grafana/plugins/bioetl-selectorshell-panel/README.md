# BioETL Selector Shell Panel

Local Grafana panel plugin for operator context shell synchronization:

1. **Exact Run ID** → resolve authoritative `workflow/pipeline/run_type` from
   `/ops/control-plane/selector-context` and write sibling variables.
2. **Last-run defaults** → when the shell is unset (`workflow=All`,
   `pipeline=unknown|All`, `run_id=-`), resolve the latest catalog run and apply
   a coherent tuple (with `run_type` fallback `backfill` when the catalog is empty).

Writes use `locationService.partial({ 'var-*': ... }, true)`.

## Scope

- Does not replace native Grafana dropdowns.
- Does not change Prometheus query semantics (`run_id` stays HTTP identity only).
- Requires local unsigned plugin loading for activation.

## Current rollout status

Plugin logic ships in-repo (`autoApplyExactRunContext` +
`autoApplyLastRunDefaults`). Shipped dashboard JSON does **not** embed the panel
by default so provisioned Grafana without the unsigned plugin does not show a
missing-panel error. Local operators enable the plugin and optionally add a
small panel (or use Explore/manual apply) for full cascade UX.

Related issues: #7550 (epic), #7555 (plugin phase).

## Local build

```bash
cd grafana/plugins/bioetl-selectorshell-panel
npm install
npm run typecheck
npm run test:ci
npm run build
```

## Grafana loading

Point Grafana plugins path at this folder (or its `dist/`) and allow:

- `bioetl-selectorshell-panel`

Example env:

```bash
GF_PLUGINS_ALLOW_LOADING_UNSIGNED_PLUGINS=bioetl-selectorshell-panel
```

## Behavior

| Condition | Action |
| --- | --- |
| Exact `run_id` selected | Fetch `?run_id=…`; write workflow/pipeline/run_type |
| Shell unset (`All`/`unknown`/`-`) | Fetch last-run context; write full shell including `run_id` |
| Catalog empty | Prefer `run_type=backfill` fallback |
| URL already carries intentional vars | Operator should open with set pipeline/run_id; panel only auto-fills when shell looks unset |

## References

- Backend: `/ops/control-plane/selector-context`, `/ops/control-plane/filter-options`
- Contract: `docs/03-guides/dashboards/contracts/selector-contracts.yaml`
- Grafana plugin variable updates: https://grafana.com/developers/plugin-tools/how-to-guides/data-source-plugins/add-support-for-variables

## Router migration candidate

The current lockfile consumes the private BioETL Router 7 bridge archive.
Deploy this artifact only with the matching patched Grafana 13.2.3 frontend
whose shared router export is Router 7.18.4. A stock host version number alone
is insufficient: an older shared Router 6 context is incompatible with the
Scenes Router 7 dependency. The integration patch and archive are maintained
in `grafana/tooling/router-v7-bridge/`.

This is a migration candidate for #11888 and #11889. The shared Grafana rollout
remains pending exact-SHA CI and runtime acceptance. Preserve the previous host
image, plugin artifacts, manifests, lockfiles, and Grafana data backup for rollback.
