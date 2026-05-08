# Standardize Dashboard Metadata, Versioning, and Tags

**Status**: Open
**Priority**: P3 (Low)
**Labels**: `dashboard`, `metadata`, `versioning`, `consistency`
**Epic**: Grafana Dashboard Improvements 2026Q2

## 🎯 Problem

Current dashboards have inconsistent metadata configurations including schemaVersion, iteration, refresh intervals, tags, and timezone settings. This makes it difficult to track dashboard versions and maintain consistent configuration across the suite.

## 🔍 Root Cause Analysis

1. **SchemaVersion Variance**: Workflow uses v39, others use v30
2. **Missing Iteration**: Only Control Plane has iteration field
3. **Inconsistent Refresh**: Different dashboards use different refresh intervals
4. **No Tag Strategy**: Some dashboards have tags, others don't
5. **Timezone Inconsistency**: Not all dashboards explicitly set timezone

## 📋 Scope

**Affected Components:**

- All dashboard JSON metadata
- schemaVersion settings
- iteration fields
- refresh configurations
- tag configurations
- timezone settings

**Impact Analysis:**

```bash
# Check schema versions
grep -rn "schemaVersion" grafana/dashboards/*.json

# Check refresh intervals
grep -rn "refresh" grafana/dashboards/*.json
```

## 🎯 Solution Plan

### Phase 1: Define Metadata Standards (1 day)

1. **Establish Versioning Strategy**

   ```yaml
   # Versioning standards
   schemaVersion:
     standard: 39
     upgrade_path: document changes
   
   iteration:
     purpose: track dashboard revisions
     increment: on significant changes
     format: integer
   ```

1. **Define Refresh Standards**

   ```yaml
   # Refresh standards
   dashboard_level_refresh:
     realtime_dashboards: "30s"
     near_realtime_dashboards: "1m"
     historical_dashboards: "5m"
   
   timepicker_intervals:
     standard: ["5s", "10s", "30s", "1m", "5m", "15m", "30m", "1h", "6h", "12h", "1d"]
   ```

1. **Define Tag Taxonomy**

   ```yaml
   # Tag taxonomy
   required_tags:
     - bioetl
   
   optional_tags:
     domain: [observability, DQ, runtime, provider, workflow]
     type: [overview, diagnostic, explorer]
     scope: [pipeline, provider, workflow]
   ```

1. **Define Timezone Standard**

   ```yaml
   # Timezone standard
   timezone:
     standard: "browser"
     explicit: true for all dashboards
   ```

### Phase 2: Update Metadata (2 days)

1. **Update schemaVersion**

   ```json
   // Update all dashboards to v39
   {
     "schemaVersion": 39
   }
   ```

1. **Add iteration Field**

   ```json
   // Add to all dashboards
   {
     "iteration": 1
   }
   ```

1. **Standardize Refresh**

   ```json
   // Apply refresh standards
   {
     "refresh": "30s", // for near-realtime
     "timepicker": {
       "refresh_intervals": ["5s", "10s", "30s", "1m", "5m", "15m", "30m", "1h", "6h", "12h", "1d"]
     }
   }
   ```

1. **Add Tags**

   ```json
   // Apply tag taxonomy
   {
     "tags": ["bioetl", "observability", "overview"] // example
   }
   ```

1. **Set Timezone**

   ```json
   // Ensure explicit timezone
   {
     "timezone": "browser"
   }
   ```

1. **Apply to All Dashboards**

   - bioetl-control-plane-v1.json ✅
   - bioetl-overview-v2.json ✅
   - bioetl-runtime.json ✅
   - bioetl-provider-health-v2.json ✅
   - bioetl-dq-v2.json ✅
   - bioetl-workflow-overview.json ✅
   - bioetl-silver-reject-explorer.json ✅

### Phase 3: Documentation (1 day)

1. **Document Versioning Strategy**

   ```markdown
   # docs/05-operations/grafana-versioning-guide.md
   ## Dashboard Versioning Strategy
   
   Schema version, iteration, and change tracking...
   ```

1. **Document Tag Taxonomy**

   ```markdown
   # docs/05-operations/grafana-tag-taxonomy.md
   ## Dashboard Tag Taxonomy
   
   Required and optional tags with definitions...
   ```

## ✅ Success Criteria

- [ ] All dashboards use schemaVersion 39
- [ ] All dashboards have iteration field
- [ ] Refresh intervals standardized
- [ ] Tags applied consistently
- [ ] Timezone explicitly set on all dashboards
- [ ] Versioning strategy documented
- [ ] Tag taxonomy documented

## 📊 Verification Commands

```bash
# Verify schema versions
grep "schemaVersion" grafana/dashboards/*.json

# Check iteration fields
grep "iteration" grafana/dashboards/*.json

# Verify tags
grep "tags" grafana/dashboards/*.json

# Validate JSON syntax
python -m json.tool grafana/dashboards/*.json > /dev/null
```

## 📈 Impact Assessment

### Positive Impacts

- **Version Tracking**: Clear dashboard revision history
- **Consistency**: Uniform metadata across dashboards
- **Discoverability**: Tags enable dashboard search/filtering
- **Maintainability**: Easier to track changes

### Potential Risks

- **Schema Version Upgrade**: May require dashboard re-import
- **Refresh Changes**: May affect user experience
- **Tag Maintenance**: Need to keep taxonomy updated

### Mitigation Strategies

- **Testing**: Test schema version upgrade in staging
- **User Communication**: Announce refresh changes
- **Tag Reviews**: Regular taxonomy reviews
- **Documentation**: Clear upgrade procedures

## 🎯 Related Issues

- **Depends On**: None
- **Related To**: All DASH-* issues

## ⏳ Time Estimate

**Total**: 4 days
**Start Date**: 2026-05-08
**Target Completion**: 2026-05-14

## 👥 Assignee

(TBD - comment on tracking issue to claim)

## 📋 Checklist

- [ ] Versioning strategy defined
- [ ] Refresh standards established
- [ ] Tag taxonomy created
- [ ] Timezone standard set
- [ ] All schemaVersions updated to 39
- [ ] All dashboards have iteration field
- [ ] Refresh intervals standardized
- [ ] Tags applied to all dashboards
- [ ] Timezone explicitly set
- [ ] Versioning guide created
- [ ] Tag taxonomy documented
- [ ] Changes tested in staging

## 🎯 Notes

This issue establishes consistent metadata across all dashboards, improving version tracking and discoverability. The standards should be followed in all future dashboard development.
