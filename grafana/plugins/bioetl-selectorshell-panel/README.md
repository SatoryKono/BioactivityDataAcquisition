# BioETL Selector Shell Panel

Local Grafana panel plugin for one specific BioETL gap:

- a user selects exact `Run ID`
- the plugin resolves authoritative `workflow/pipeline/run_type` from
  `/ops/control-plane/selector-context`
- the plugin writes those values back into visible dashboard variables via
  `locationService.partial({ 'var-*': ... }, true)`

This is the supported Grafana mechanism for plugin-side variable updates.

## Scope

The plugin is intentionally narrow:

- it does not replace the shipped native selector shell
- it does not change Prometheus query semantics
- it exists to synchronize visible dashboard selectors when exact `run_id`
  identity is selected

## Current rollout status

The plugin is implemented as a local repo surface and can be built/tested
independently. It is **not yet wired into shipped dashboard JSON** by default,
because production activation also requires local Grafana plugin loading for
unsigned plugins.

## Local build

```bash
cd grafana/plugins/bioetl-selectorshell-panel
npm install
npm run typecheck
npm run test:ci
npm run build
```

## Expected placement

Grafana scans plugin directories for folders containing `plugin.json`. If the
folder contains a `dist/` subdirectory, Grafana mounts `dist/` instead of the
source folder.

For local BioETL environments, point Grafana plugin loading at this plugin
folder or copy its built `dist/` output into the local Grafana plugin
directory, then allow the unsigned plugin id:

- `bioetl-selectorshell-panel`

## Panel behavior

- If `run_id = "-"`, the panel stays idle.
- If exact `run_id` is selected, it fetches
  `/ops/control-plane/selector-context?run_id=<id>`.
- If the resolved `workflow/pipeline/run_type` differs from the visible shell,
  it updates `var-workflow`, `var-pipeline`, and `var-run_type` in place.
- If auto-apply is disabled, the panel renders an explicit apply button.

## References

- Grafana plugin basics: https://grafana.com/docs/grafana/latest/developers/plugins/create-a-grafana-plugin/develop-a-plugin/build-a-panel-plugin/
- Grafana variable updates from plugins: https://grafana.com/developers/plugin-tools/how-to-guides/data-source-plugins/add-support-for-variables
