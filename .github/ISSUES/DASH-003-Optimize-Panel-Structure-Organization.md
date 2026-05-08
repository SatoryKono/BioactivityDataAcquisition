# Optimize Panel Structure and Organization Across All Dashboards

**Status**: Open
**Priority**: P2 (Medium)
**Labels**: `dashboard`, `UX`, `organization`, `consistency`
**Epic**: Grafana Dashboard Improvements 2026Q2

## 🎯 Problem

Current dashboards have inconsistent panel organization, making it difficult for operators to quickly assess system health and locate relevant information. Some dashboards are cluttered with too many panels on the first screen, while others lack proper grouping of related information.

## 🔍 Root Cause Analysis

1. **No Collapsible Row Strategy**: Runtime and Control Plane use collapsible rows, others don't
2. **First-Screen Clutter**: Some dashboards show too many panels at once
3. **Poor Information Hierarchy**: Important status panels mixed with detailed diagnostics
4. **Inconsistent Grouping**: Related panels not grouped together
5. **No Standard Layout**: Each dashboard uses different layout patterns

## 📋 Scope

**Affected Components:**

- All dashboard JSON files in `grafana/dashboards/`
- Panel grid positioning
- Collapsible row configuration
- Panel grouping and hierarchy

**Impact Analysis:**

```bash
# Count panels per dashboard
jq '.panels | length' grafana/dashboards/*.json
```

## 🎯 Solution Plan

### Phase 1: Define Panel Organization Standard (1 day)

1. **Establish First-Screen Standard**

   ```yaml
   # First screen should contain:
   first_screen_max_panels: 8
   first_screen_content:
     - navigation_header
     - scope_banner
     - current_status_row (max 4 key metrics)
     - next_action_guidance
   ```

1. **Define Collapsible Row Strategy**

   ```yaml
   # Collapsible row usage
   collapsible_rows:
     overview_dashboard: not_needed
     runtime_dashboard: 
       - logs_traces_drilldown
     control_plane_dashboard:
       - replay_diagnostics
       - checkpoint_diagnostics
     DQ_dashboard: not_needed
     provider_health_dashboard: not_needed
     workflow_dashboard: not_needed
     silver_explorer: not_needed
   ```

1. **Define Panel Grouping Rules**

   ```yaml
   # Panel grouping hierarchy
   grouping:
     level_1: current_status (always visible)
     level_2: kpi_summary (always visible)
     level_3: detailed_evidence (collapsible if extensive)
     level_4: forensic_drilldown (collapsible)
   ```

### Phase 2: Reorganize All Dashboards (4 days)

1. **Reorganize Overview Dashboard**

   ```json
   // First screen: status, next action, L0 inputs
   // Collapsible: detailed diagnostics
   ```

1. **Reorganize Runtime Dashboard**

   ```json
   // First screen: current status, telemetry gap, KPIs
   // Collapsible: detailed blockers, logs/traces
   ```

1. **Reorganize Control Plane Dashboard**

   ```json
   // First screen: replay safety, manifest/ledger, telemetry
   // Collapsible: detailed replay diagnostics
   ```

1. **Reorganize DQ Dashboard**

   ```json
   // First screen: current status, threshold state, reasons
   // Below fold: range evidence panels
   ```

1. **Reorganize Provider Health Dashboard**

   ```json
   // First screen: severity matrix, critical providers, top causes
   // Below fold: detailed health metrics
   ```

1. **Reorganize Workflow Dashboard**

   ```json
   // First screen: failed runs/steps, skipped events
   // Below fold: detailed workflow evidence
   ```

1. **Reorganize Silver Reject Explorer**

   ```json
   // First screen: total rejects, reject rate, scope summary
   // Below fold: detailed breakdown and record table
   ```

### Phase 3: Validation and Testing (1 day)

1. **Test First-Screen Layout**

   ```bash
   # Manual verification
   - All dashboards load without scrolling on standard screens
   - Key information visible at first glance
   - Navigation to details intuitive
   ```

1. **Verify Collapsible Row Functionality**

   ```bash
   # Test collapsible rows
   - Rows expand/collapse correctly
   - State preserved across refresh
   - Default collapse state appropriate
   ```

## ✅ Success Criteria

- [ ] All dashboards follow first-screen standard (≤8 panels)
- [ ] Collapsible rows used consistently where appropriate
- [ ] Panel grouping follows defined hierarchy
- [ ] Important status panels always visible
- [ ] Detailed diagnostics properly organized
- [ ] Layout standards documented

## 📊 Verification Commands

```bash
# Count panels on first screen (y < 10)
jq '.panels | map(select(.gridPos.y < 10)) | length' grafana/dashboards/*.json

# Check collapsible row usage
grep -rn "collapsed" grafana/dashboards/*.json

# Validate JSON syntax
python -m json.tool grafana/dashboards/*.json > /dev/null
```

## 📈 Impact Assessment

### Positive Impacts

- **Usability**: Operators can quickly assess system health
- **Efficiency**: Less time spent finding relevant information
- **Consistency**: Uniform layout patterns across dashboards
- **Reduced Cognitive Load**: Clear information hierarchy

### Potential Risks

- **User Adaptation**: Users accustomed to current layouts
- **Information Hiding**: Collapsed rows might hide important info
- **Testing Overhead**: Manual layout verification required

### Mitigation Strategies

- **Documentation**: Document new layout patterns
- **User Testing**: Get feedback on new layouts
- **Gradual Rollout**: Deploy to staging first
- **Default States**: Set appropriate default collapse states

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

- [ ] Panel organization standard documented
- [ ] Collapsible row strategy defined
- [ ] Panel grouping rules established
- [ ] Overview dashboard reorganized
- [ ] Runtime dashboard reorganized
- [ ] Control Plane dashboard reorganized
- [ ] DQ dashboard reorganized
- [ ] Provider Health dashboard reorganized
- [ ] Workflow dashboard reorganized
- [ ] Silver Reject Explorer reorganized
- [ ] First-screen layouts verified
- [ ] Collapsible rows tested
- [ ] Documentation updated
- [ ] Changes deployed to staging

## 🎯 Notes

This issue improves dashboard usability by establishing clear information hierarchy and consistent organization patterns. The standard should be included in the dashboard development guide.
