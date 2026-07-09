______________________________________________________________________

Version: 1.1.0
Status: in_progress
Class: plan
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-07'

______________________________________________________________________

# Dashboard Datasource UID Refactoring Plan

## Context

Follow-up review of the 2026-05-07 dashboard audit confirmed one real
provisioning-risky inconsistency and one broader style drift across the shipped
Grafana dashboards:

- `bioetl-dq-v2.json` contains three Prometheus target datasource objects with
  `uid: "${DS_PROMETHEUS}"`, while the provisioned datasource UID is
  `prometheus`
- several shipped dashboards still use string panel datasource references
  (`"datasource": "Prometheus"`) while newer panels already use explicit object
  references with `type` + `uid`

The repository already has Grafana integration contracts and dashboard test
support, so this refactor should extend those surfaces rather than introduce a
parallel ad-hoc checker.

## Problem Statement

### Confirmed Issues

1. **Provisioning-sensitive UID mismatch**
   - `grafana/dashboards/bioetl-dq-v2.json` uses
     `{"type": "prometheus", "uid": "${DS_PROMETHEUS}"}`
     in three target datasource blocks
   - `grafana/provisioning/datasources-core/prometheus.yml` provisions the
     datasource with `uid: prometheus`
   - Risk: target resolution may drift or fail after provisioning/import

2. **Inconsistent Prometheus panel datasource style**
   - some shipped Prometheus panels still use `"datasource": "Prometheus"`
   - other shipped Prometheus panels already use
     `{"type": "prometheus", "uid": "prometheus"}`
   - Risk: style drift, weaker explicitness, and less robust behavior if the
     datasource display name changes

### Non-Goals

This refactor does **not**:

- rewrite `templating.list[*].datasource` surfaces unless a separate task
  intentionally broadens that scope
- change non-Prometheus datasources such as `Quarantine Explorer` or
  `-- Grafana --`
- add datasource policy to
  `docs/03-guides/dashboards/contracts/navigation-links.yaml`, which remains
  the SSOT for link/time semantics only
- create a new standalone CI script when the existing Grafana integration suite
  can enforce the contract

## Objectives

1. Replace all `${DS_PROMETHEUS}` target UID references in shipped dashboards
   with `uid: "prometheus"`
2. Standardize shipped **Prometheus panel datasource** references to object
   format with explicit `type` and `uid`
3. Enforce the contract in the existing Grafana integration test suite
4. Update Grafana documentation with the narrow, explicit datasource standard
5. Validate changed dashboards with targeted JSON and integration checks

## Confirmed Scope

### Dashboard JSON files in scope

- `grafana/dashboards/bioetl-control-plane-v1.json`
- `grafana/dashboards/bioetl-dq-v2.json`
- `grafana/dashboards/bioetl-overview-v2.json`
- `grafana/dashboards/bioetl-provider-health-v2.json`
- `grafana/dashboards/bioetl-runtime.json`
- `grafana/dashboards/bioetl-workflow-overview.json`

### Dashboard JSON file explicitly out of panel-datasource rewrite scope

- `grafana/dashboards/bioetl-silver-reject-explorer.json`
  Reason: its shipped panel datasources are intentionally `Quarantine Explorer`;
  Prometheus appears there in template-variable context, not in a shipped panel
  datasource field that this wave standardizes.

### Test and doc surfaces in scope

- `tests/integration/test_grafana_config.py`
- `grafana/README.md`

## Implementation Plan

### Phase 1: Fix shipped dashboard JSON

#### 1.1 Remove `${DS_PROMETHEUS}` from DQ target datasource blocks

Update the three target datasource objects in
`grafana/dashboards/bioetl-dq-v2.json` from:

```json
{
  "type": "prometheus",
  "uid": "${DS_PROMETHEUS}"
}
```

to:

```json
{
  "type": "prometheus",
  "uid": "prometheus"
}
```

#### 1.2 Standardize Prometheus panel datasource references

For shipped Prometheus **panel** datasource fields in the scoped dashboards,
replace:

```json
"datasource": "Prometheus"
```

with:

```json
"datasource": {
  "type": "prometheus",
  "uid": "prometheus"
}
```

Important scope rule:

- update panel datasource fields only
- do not rewrite template-variable datasource fields in this wave

### Phase 2: Extend existing Grafana integration tests

Add datasource consistency assertions to `tests/integration/test_grafana_config.py`
instead of introducing a new standalone CI script.

The new test should:

- walk shipped panels through existing recursive helpers
- assert that scoped Prometheus panels no longer use string datasource format
- assert that Prometheus datasource objects use `type=prometheus` and
  `uid=prometheus`
- assert that `${DS_PROMETHEUS}` no longer appears in target datasource blocks
- continue tolerating non-Prometheus datasources where intentionally used

### Phase 3: Update documentation

Add a narrow datasource standard section to `grafana/README.md`:

- Prometheus **panel** datasource references should use explicit object format
- the provisioned Prometheus datasource UID is `prometheus`
- `${DS_PROMETHEUS}` must not appear in shipped dashboard JSON
- template-variable datasource handling is outside the scope of this specific
  normalization rule unless the repo standard is intentionally widened later

### Phase 4: Validation

Run the smallest sufficient verification set:

```bash
python -m json.tool grafana/dashboards/bioetl-control-plane-v1.json > /dev/null
python -m json.tool grafana/dashboards/bioetl-dq-v2.json > /dev/null
python -m json.tool grafana/dashboards/bioetl-overview-v2.json > /dev/null
python -m json.tool grafana/dashboards/bioetl-provider-health-v2.json > /dev/null
python -m json.tool grafana/dashboards/bioetl-runtime.json > /dev/null
python -m json.tool grafana/dashboards/bioetl-workflow-overview.json > /dev/null
uv run python -m pytest -q tests/integration/test_grafana_config.py
```

Optional live validation can follow in a separate deployment-facing task if the
workspace owner wants a local Grafana provisioning smoke.

## Success Criteria

1. `grafana/dashboards/` contains no `${DS_PROMETHEUS}` target datasource UID
   references
2. all scoped Prometheus panel datasource references use explicit object format
3. existing Grafana integration tests enforce the datasource contract
4. `grafana/README.md` documents the shipped Prometheus panel datasource rule
5. targeted JSON and Grafana integration validation passes

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Over-broad rewrite touches template variables | Medium | Medium | Limit rewrite to shipped panel/target datasource fields only |
| New test misses nested row panels | Medium | High | Reuse existing recursive `get_dashboard_panels()` helper |
| Docs drift from runtime truth | Low | Medium | Keep JSON as SSOT and update docs in the same change set |
| CI duplication with existing Grafana suite | High | Low | Extend `tests/integration/test_grafana_config.py` instead of adding a parallel checker |

## Execution Status

- [x] Repo review against shipped dashboards, provisioning config, and CI
- [x] Plan narrowed to real repo scope
- [ ] Dashboard JSON changes applied
- [ ] Grafana integration test extended
- [ ] Grafana docs synchronized
- [ ] Targeted validation complete

## References

- `grafana/provisioning/datasources-core/prometheus.yml`
- `grafana/dashboards/*.json`
- `tests/integration/_grafana_test_support.py`
- `tests/integration/test_grafana_config.py`
- `docs/03-guides/dashboards/dashboard-extension-llm.md`

______________________________________________________________________
