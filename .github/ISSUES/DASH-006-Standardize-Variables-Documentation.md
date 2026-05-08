# Standardize Variables and Create Unified Documentation

**Status**: Open
**Priority**: P2 (Medium)
**Labels**: `dashboard`, `documentation`, `consistency`, `UX`
**Epic**: Grafana Dashboard Improvements 2026Q2

## 🎯 Problem

Current dashboards use different variable sets and behaviors without comprehensive documentation. Some dashboards have unique variables (reason_code, field, run_id, payload_hash, workflow, step_kind, step_status) that are not documented in a unified reference. Variable behavior (single-select vs multi-select, fail-closed vs fallback) is inconsistent.

## 🔍 Root Cause Analysis

1. **No Variable Reference**: No unified documentation of all dashboard variables
2. **Inconsistent Behavior**: Same variable names behave differently across dashboards
3. **Undocumented Variables**: Special-purpose variables lack clear documentation
4. **No Selection Strategy**: No standard for single vs multi-select patterns
5. **Fail-Closed Inconsistency**: Some variables default to unknown, others to All

## 📋 Scope

**Affected Components:**

- All dashboard variable configurations in `grafana/dashboards/*.json`
- Variable documentation
- Variable behavior definitions
- Variable dependency chains

**Impact Analysis:**

```bash
# Count variable configurations
grep -rn "templating" grafana/dashboards/*.json

# Count unique variable names
jq '.templating.list[].name' grafana/dashboards/*.json | sort -u
```

## 🎯 Solution Plan

### Phase 1: Create Variable Reference (1 day)

1. **Inventory All Variables**

   ```yaml
   # Variable inventory
   common_variables:
     pipeline:
       type: query
       datasource: Prometheus
       behavior: single-select
       fail_closed: true
       default: unknown
     
     run_type:
       type: query
       datasource: Prometheus
       behavior: multi-select
       default: All
     
     stage:
       type: query
       datasource: Prometheus
       behavior: multi-select
       default: unknown
   
   dashboard_specific:
     reason_code: # Silver Reject Explorer
     field: # Silver Reject Explorer
     run_id: # Silver Reject Explorer
     payload_hash: # Silver Reject Explorer
     workflow: # Workflow Overview
     status: # Workflow Overview
     step_kind: # Workflow Overview
     step_status: # Workflow Overview
   ```

1. **Define Variable Behavior Standards**

   ```yaml
   # Variable behavior standards
   selection_mode:
     single_select:
       use_when: single entity required
       examples: pipeline, run_id, workflow
     
     multi_select:
       use_when: multiple entities acceptable
       examples: run_type, stage, status, step_kind
   
   fail_closed:
     use_when: scope must be explicit
     default: unknown
     examples: pipeline, run_id
   
   fallback:
     use_when: aggregate scope acceptable
     default: All
     examples: run_type, stage, status
   ```

1. **Create Variable Reference Document**

   ```markdown
   # docs/05-operations/grafana-variable-reference.md
   ## Dashboard Variable Reference
   
   Complete reference for all dashboard variables...
   ```

### Phase 2: Update Variable Descriptions (2 days)

1. **Add Variable Descriptions**

   ```json
   // Add description to all variables
   {
     "name": "pipeline",
     "description": "Core scope: one concrete pipeline for dashboard scope. Single-select; fail-closed with unknown default."
   }
   ```

1. **Standardize Variable Defaults**

   ```json
   // Standardize default values
   {
     "pipeline": {"current": {"text": "unknown", "value": "unknown"}},
     "run_type": {"current": {"text": "All", "value": "$__all"}},
     "stage": {"current": {"text": "unknown", "value": "unknown"}}
   }
   ```

1. **Update Variable Dependencies**

   ```json
   // Ensure proper variable dependencies
   {
     "name": "run_type",
     "query": "label_values(..., run_type)",
     "dependsOn": ["pipeline"]
   }
   ```

### Phase 3: Document and Validate (1 day)

1. **Complete Variable Reference**

   ```markdown
   # Document all variables with:
   # - Purpose and scope
   # - Data source
   # - Selection mode
   # - Default behavior
   # - Dependencies
   # - Usage examples
   ```

1. **Validate Variable Configurations**

   ```bash
   # Verify all variables have descriptions
   jq '.templating.list[] | select(.description == null)' grafana/dashboards/*.json

   # Check variable dependencies
   # Manual verification required
   ```

## ✅ Success Criteria

- [ ] Complete variable inventory created
- [ ] Variable behavior standards documented
- [ ] Unified variable reference document created
- [ ] All dashboard variables have descriptions
- [ ] Variable defaults standardized
- [ ] Variable dependencies documented
- [ ] Reference document published

## 📊 Verification Commands

```bash
# Verify variable descriptions
jq '.templating.list[] | select(.description != null) | length' grafana/dashboards/*.json

# Check variable defaults consistency
jq '.templating.list[].current' grafana/dashboards/*.json

# Validate JSON syntax
python -m json.tool grafana/dashboards/*.json > /dev/null
```

## 📈 Impact Assessment

### Positive Impacts

- **Documentation**: Clear reference for all dashboard variables
- **Consistency**: Uniform variable behavior across dashboards
- **Usability**: Operators understand variable purpose and behavior
- **Maintainability**: Easier to add new variables following standards

### Potential Risks

- **Documentation Maintenance**: Need to keep reference updated
- **Breaking Changes**: Variable default changes may affect workflows
- **Complexity**: Additional documentation to maintain

### Mitigation Strategies

- **Automated Validation**: Script to check variable documentation
- **Version Control**: Track variable changes in commits
- **User Review**: Get feedback on variable behavior changes
- **Documentation Reviews**: Regular review of reference accuracy

## 🎯 Related Issues

- **Depends On**: DASH-001 (Navigation)
- **Related To**: All DASH-* issues

## ⏳ Time Estimate

**Total**: 4 days
**Start Date**: 2026-05-08
**Target Completion**: 2026-05-14

## 👥 Assignee

(TBD - comment on tracking issue to claim)

## 📋 Checklist

- [ ] Variable inventory completed
- [ ] Variable behavior standards defined
- [ ] Variable reference document created
- [ ] All variable descriptions added
- [ ] Variable defaults standardized
- [ ] Variable dependencies documented
- [ ] Reference document reviewed
- [ ] Variable configurations validated
- [ ] Documentation published

### Current Implementation Status

**Completed:**
- Variable behavior standards defined
- Variable reference document structure defined

**Current Variable State:**
- All dashboards have templating section with variables
- Variable descriptions: Most variables lack descriptions - needs review
- Variable defaults: Inconsistent across dashboards - needs standardization
- Variable dependencies: Not consistently documented - needs review

**Variable Inventory (preliminary):**
- Common variables: pipeline, run_type, stage (present in most dashboards)
- Dashboard-specific:
  - bioetl-workflow-overview: workflow, status, step_kind, step_status
  - bioetl-silver-reject-explorer: reason_code, field, run_id, payload_hash

**Remaining:**
- Complete variable inventory for all dashboards
- Add descriptions to all variables
- Standardize variable defaults
- Document variable dependencies
- Create comprehensive variable reference document
- Validate variable configurations

## 🎯 Notes

This issue creates comprehensive documentation for all dashboard variables, improving usability and maintainability. The reference should be kept updated as part of the dashboard development process.
