# Standardize Navigation and Variable Passing Across All Dashboards

**Status**: Open
**Priority**: P1 (High)
**Labels**: `dashboard`, `navigation`, `UX`, `consistency`
**Epic**: Grafana Dashboard Improvements 2026Q2

## 🎯 Problem

Current dashboards have inconsistent navigation patterns and variable passing between dashboards. This creates confusion for operators and makes it difficult to maintain consistent context when drilling down from overview to detailed dashboards.

## 🔍 Root Cause Analysis

1. **Inconsistent Link Order**: Different dashboards use different ordering of navigation links
2. **Variable Passing Inconsistency**: Workflow dashboard resets pipeline/run_type to unknown/All, while others preserve context
3. **Context Mapping Issues**: Provider Health uses `pipeline_context` instead of `pipeline` for return context preservation
4. **Missing/Extra Links**: Some dashboards include Explore Logs/Traces links, others don't
5. **No Standard Pattern**: Each dashboard implements navigation independently

## 📋 Scope

**Affected Components:**

- `grafana/dashboards/bioetl-control-plane-v1.json`
- `grafana/dashboards/bioetl-overview-v2.json`
- `grafana/dashboards/bioetl-runtime.json`
- `grafana/dashboards/bioetl-provider-health-v2.json`
- `grafana/dashboards/bioetl-dq-v2.json`
- `grafana/dashboards/bioetl-workflow-overview.json`
- `grafana/dashboards/bioetl-silver-reject-explorer.json`
а также  Explore Logs и Explore Traces 
**Impact Analysis:**

```bash
# Count navigation inconsistencies across dashboards
grep -rn "var-pipeline\|var-run_type" grafana/dashboards/*.json | wc -l
```

## 🎯 Solution Plan

### Phase 1: Define Navigation Standard (1 day)

1. **Establish Standard Link Order**

   ```
   0. Control Plane → 1. Overview → 2. Runtime → 3. Provider Health → 4. Data Quality → 5. Workflow -> 6. Silver Reject Explorer > 7. Explore Logs -> 8. Explore Traces

   ```

1. **Define Variable Passing Rules**

   ```yaml
   # Standard variable passing rules
   preserve_context:
     - pipeline: preserve when navigating from overview/runtime/DQ
     - run_type: preserve when navigating from overview/runtime/DQ
     - stage: preserve when navigating from runtime to DQ
   
   reset_context:
     - workflow: always reset to unknown/All (workflow-level scope)
     - provider: use unknown fail-closed, preserve pipeline_context
   ```

1. **Standardize Explore Links**

   ```yaml
   include_explore_links:
     - overview: yes
     - runtime: yes
     - DQ: yes
     - control_plane: no
     - provider_health: no
     - workflow: no
   ```

### Phase 2: Update All Dashboards (3 days)

1. **Update Navigation HTML Panels**

   ```json
   // Standard navigation panel content
   {
     "content": "<div style=\"display:flex;gap:10px;flex-wrap:wrap;padding:10px;\">
       <a href=\"/d/bioetl-control-plane-v1/...\">0. Control Plane</a>
       <a href=\"/d/bioetl-overview-v2/...\">1. Overview</a>
       <a href=\"/d/bioetl-runtime/...\">2. Runtime</a>
       <a href=\"/d/bioetl-provider-health-v2/...\">3. Provider Health</a>
       <a href=\"/d/bioetl-dq-v2/...\">4. Data Quality</a>
       <a href=\"/d/bioetl-workflow-overview/...\">5. Workflow</a>
     </div>"
   }
   ```

1. **Update Link URLs with Standard Variable Passing**

   ```json
   // Preserve context links
   {
     "url": "/d/bioetl-runtime/bioetl-runtime?var-pipeline=$pipeline&var-run_type=$run_type&var-stage=$stage&${__url_time_range}"
   }
   
   // Reset context links (workflow)
   {
     "url": "/d/bioetl-workflow-overview/bioetl-workflow-overview?${__url_time_range}"
   }
   
   // Provider health with context preservation
   {
     "url": "/d/bioetl-provider-health-v2/...?var-provider=unknown&var-pipeline_context=$pipeline&var-adapter=unknown&${__url_time_range}"
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

### Phase 3: Validation and Testing (1 day)

1. **Test Navigation Flows**

   ```bash
   # Manual testing checklist
   - Navigate from Overview to Runtime: context preserved ✓
   - Navigate from Runtime to DQ: context preserved ✓
   - Navigate from any dashboard to Workflow: context reset ✓
   - Navigate to Provider Health: pipeline_context preserved ✓
   ```

1. **Verify Link Functionality**

   ```bash
   # Test all dashboard links
   # (Manual verification required)
   ```

## ✅ Success Criteria

- [ ] All dashboards use consistent link order (0-5)
- [ ] Variable passing rules standardized and documented
- [ ] Context preservation works correctly for all navigation flows
- [ ] Explore Logs/Traces links included where appropriate
- [ ] No broken links across dashboards
- [ ] Navigation documented in dashboard guide

## 📊 Verification Commands

```bash
# Verify link order consistency
grep -A 5 "content.*display:flex" grafana/dashboards/*.json

# Check variable passing patterns
grep "var-pipeline=" grafana/dashboards/*.json

# Validate JSON syntax
python -m json.tool grafana/dashboards/*.json > /dev/null
```

## 📈 Impact Assessment

### Positive Impacts

- **Consistency**: Uniform navigation experience across all dashboards
- **Usability**: Operators can predict navigation behavior
- **Efficiency**: Context preservation reduces need to re-select variables
- **Maintainability**: Standard pattern makes updates easier

### Potential Risks

- **Breaking Changes**: Users accustomed to current navigation patterns
- **Context Confusion**: Some workflows may rely on current reset behavior
- **Testing Overhead**: Manual testing required for all navigation flows

### Mitigation Strategies

- **Documentation**: Clearly document new navigation behavior
- **Gradual Rollout**: Deploy to staging first
- **User Communication**: Announce changes before deployment
- **Fallback Plan**: Keep backup of current dashboard versions

## 🎯 Related Issues

- **Depends On**: None
- **Blocks**: DASH-002 (Color Scheme), DASH-003 (Panel Structure)
- **Related To**: All DASH-* issues

## ⏳ Time Estimate

**Total**: 5 days
**Start Date**: 2026-05-08
**Target Completion**: 2026-05-15

## 👥 Assignee

(TBD - comment on tracking issue to claim)

## 📋 Checklist

- [ ] Navigation standard documented
- [ ] Variable passing rules defined
- [ ] All dashboard navigation panels updated
- [ ] All dashboard link URLs updated
- [ ] Navigation flows tested manually
- [ ] Documentation updated
- [ ] Changes deployed to staging
- [ ] User communication sent

## 🎯 Notes

This issue establishes the foundation for consistent dashboard navigation across the entire Grafana observability stack. The standard should be documented in a dashboard guide and referenced in all future dashboard development.
