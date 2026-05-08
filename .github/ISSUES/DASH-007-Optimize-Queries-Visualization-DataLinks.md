# Optimize Queries, Visualization, and DataLinks Across All Dashboards

**Status**: Open
**Priority**: P2 (Medium)
**Labels**: `dashboard`, `performance`, `visualization`, `consistency`
**Epic**: Grafana Dashboard Improvements 2026Q2

## 🎯 Problem

Current dashboards have inconsistent query patterns, visualization settings, and dataLink configurations. Some panels have multiple dataLinks while others have none, creating inconsistent drill-down experiences. Duplicate queries may exist, and visualization settings are not standardized.

## 🔍 Root Cause Analysis

1. **Duplicate Queries**: Same metrics queried multiple times across panels
2. **Inconsistent Visualization**: Different panels use different visualization settings for similar data
3. **DataLink Variance**: Some panels have many dataLinks, others have none
4. **Inconsistent Patterns**: targetBlank, includeVars usage varies
5. **No Drill-Down Standards**: No standard for panel-to-panel navigation

## 📋 Scope

**Affected Components:**

- All dashboard panel configurations
- Query definitions
- Visualization settings
- dataLink configurations
- Recording rule usage

**Impact Analysis:**

```bash
# Count query patterns
grep -rn "expr" grafana/dashboards/*.json | wc -l

# Count dataLinks
grep -rn "dataLinks" grafana/dashboards/*.json | wc -l
```

## 🎯 Solution Plan

### Phase 1: Define Query and Visualization Standards (1 day)

1. **Establish Query Standards**

   ```yaml
   # Query standards
   use_recording_rules:
     preference: always_use_recording_rules
     reason: performance and consistency
   
   avoid_duplicates:
     check: panel-to-panel query comparison
     action: consolidate or reference
   
   query_patterns:
     current_status: use 15m recording rules
     range_evidence: use $__interval
     instant: use instant queries for current state
   ```

1. **Define Visualization Standards**

   ```yaml
   # Visualization standards
   stat_panels:
     current_status: colorMode=background
     trend_metrics: colorMode=value
     counts: graphMode=area
   
   gauge_panels:
     percentages: showThresholdMarkers=true
     scores: showThresholdLabels=false
   
   table_panels:
     status: cellOptions=color-background
     data: cellOptions=auto
   ```

1. **Define DataLink Standards**

   ```yaml
   # DataLink standards
   panel_types:
     stat:
       max_links: 3
       required: [runbook_link]
       optional: [drilldown_link]
     
     table:
       max_links: 5
       required: [runbook_link]
       optional: [drilldown_links]
   
   link_behavior:
     runbook: targetBlank=true
     drilldown: targetBlank=false
     external: targetBlank=true
   ```

### Phase 2: Optimize Queries (2 days)

1. **Identify Duplicate Queries**

   ```bash
   # Script to find duplicate queries
   python scripts/analyze_dashboard_queries.py --find-duplicates
   ```

1. **Consolidate or Reference**

   ```json
   // Option 1: Consolidate into single panel
   // Option 2: Use panel reference if supported
   // Option 3: Accept duplication if justified
   ```

1. **Standardize Recording Rule Usage**

   ```json
   // Use recording rules where available
   {
     "expr": "bioetl_runtime_current_status{...}"
     // Instead of raw metric calculation
   }
   ```

### Phase 3: Standardize Visualization and DataLinks (2 days)

1. **Update Visualization Settings**

   ```json
   // Apply visualization standards
   {
     "options": {
       "colorMode": "background", // for status
       "graphMode": "area", // for trends
       "showThresholdMarkers": true
     }
   }
   ```

1. **Standardize DataLinks**

   ```json
   // Standard dataLink configuration
   {
     "dataLinks": [
       {
         "title": "Open Runbook",
         "url": "https://github.com/.../runbook.md",
         "targetBlank": true
       },
       {
         "title": "Drill Down",
         "url": "/d/other-dashboard/...",
         "targetBlank": false
       }
     ]
   }
   ```

1. **Add Tooltip Enhancements**

   ```json
   // Standard tooltip configuration
   {
     "options": {
       "tooltip": {
         "mode": "multi",
         "sort": "desc"
       }
     }
   }
   ```

### Phase 4: Validation and Documentation (1 day)

1. **Validate Query Performance**

   ```bash
   # Test query performance
   # Manual verification in Grafana
   ```

1. **Test DataLink Functionality**

   ```bash
   # Verify all links work correctly
   # Manual verification required
   ```

1. **Document Standards**

   ```markdown
   # docs/05-operations/grafana-query-visualization-standards.md
   ## Query and Visualization Standards
   
   All dashboards must follow query and visualization standards...
   ```

## ✅ Success Criteria

- [ ] Duplicate queries identified and addressed
- [ ] Recording rules used where available
- [ ] Visualization settings standardized
- [ ] DataLink patterns consistent
- [ ] Tooltip configurations enhanced
- [ ] Query and visualization standards documented

## 📊 Verification Commands

```bash
# Check for duplicate queries
python scripts/analyze_dashboard_queries.py --find-duplicates

# Verify dataLink consistency
grep -rn "dataLinks" grafana/dashboards/*.json

# Validate JSON syntax
python -m json.tool grafana/dashboards/*.json > /dev/null
```

## 📈 Impact Assessment

### Positive Impacts

- **Performance**: Reduced duplicate queries
- **Consistency**: Uniform visualization patterns
- **Usability**: Consistent drill-down experience
- **Maintainability**: Standard patterns easier to maintain

### Potential Risks

- **Breaking Changes**: Visualization changes may affect user experience
- **Query Complexity**: Consolidation may increase query complexity
- **Testing Overhead**: Manual verification required for links

### Mitigation Strategies

- **Gradual Rollout**: Deploy to staging first
- **User Testing**: Get feedback on visualization changes
- **Performance Testing**: Verify query performance
- **Documentation**: Document all changes clearly

## 🎯 Related Issues

- **Depends On**: DASH-001 (Navigation), DASH-002 (Color Scheme)
- **Related To**: All DASH-* issues

## ⏳ Time Estimate

**Total**: 6 days
**Start Date**: 2026-05-08
**Target Completion**: 2026-05-16

## 👥 Assignee

(TBD - comment on tracking issue to claim)

## 📋 Checklist

- [ ] Query standards documented
- [ ] Visualization standards defined
- [ ] DataLink standards established
- [ ] Duplicate queries identified
- [ ] Recording rule usage standardized
- [ ] Visualization settings updated
- [ ] DataLink configurations standardized
- [ ] Tooltip configurations enhanced
- [ ] Query performance validated
- [ ] DataLinks tested
- [ ] Standards documented
- [ ] Changes deployed to staging

### Current Implementation Status

**Completed:**
- Query standards documented
- Visualization standards defined
- DataLink standards established

**Current dataLinks State:**
- bioetl-runtime.json: 24 dataLinks instances (mix of populated and empty arrays)
- bioetl-control-plane-v1.json: 27 dataLinks instances
- bioetl-overview-v2.json: 10 dataLinks instances
- bioetl-dq-v2.json: 18 dataLinks instances
- bioetl-silver-reject-explorer.json: 5 dataLinks instances
- bioetl-provider-health-v2.json: 8 dataLinks instances
- bioetl-workflow-overview.json: TBD - needs review

**Current Query State:**
- Recording rule usage: Mixed - some use raw metrics, others use recording rules
- Duplicate queries: Not yet analyzed - needs investigation
- Visualization settings: Inconsistent across dashboards - needs standardization

**Remaining:**
- Identify and consolidate duplicate queries
- Standardize recording rule usage
- Apply visualization standards to all panels
- Standardize dataLink patterns
- Add tooltip enhancements
- Validate query performance
- Test dataLink functionality
- Document final standards

## 🎯 Notes

This issue improves dashboard performance and consistency by standardizing queries, visualization, and drill-down patterns. The standards should be included in the dashboard development guide.
