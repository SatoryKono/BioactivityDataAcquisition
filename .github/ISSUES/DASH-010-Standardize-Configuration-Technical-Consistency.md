# Standardize Configuration and Technical Consistency Across All Dashboards

**Status**: Open
**Priority**: P3 (Low)
**Labels**: `dashboard`, `configuration`, `technical-debt`, `consistency`
**Epic**: Grafana Dashboard Improvements 2026Q2

## 🎯 Problem

Current dashboards have inconsistent technical configurations including pluginVersion (within and between dashboards), style settings, and other base configurations. This creates technical debt and makes maintenance more difficult.

## 🔍 Root Cause Analysis

1. **pluginVersion Variance**: Different panels use different plugin versions (10.4.0 vs 12.2.0)
2. **Style Inconsistency**: Not all dashboards explicitly set style
3. **No Configuration Standard**: Each dashboard configured independently
4. **Technical Debt**: Inconsistent configurations accumulate over time
5. **No Validation**: No automated checks for configuration consistency

## 📋 Scope

**Affected Components:**

- All dashboard panel pluginVersion settings
- Dashboard-level style configurations
- Other base technical configurations
- Configuration validation

**Impact Analysis:**

```bash
# Check plugin versions
grep -rn "pluginVersion" grafana/dashboards/*.json

# Check style settings
grep -rn "style" grafana/dashboards/*.json
```

## 🎯 Solution Plan

### Phase 1: Define Configuration Standards (1 day)

1. **Establish pluginVersion Standard**

   ```yaml
   # pluginVersion standards
   target_version: "12.2.0"
   
   upgrade_strategy:
     - upgrade all panels to target version
     - test compatibility
     - document any breaking changes
   ```

1. **Define Style Standard**

   ```yaml
   # Style standards
   style:
     dark_mode: true
     explicit: true for all dashboards
   
   base_settings:
     editable: true
     graphTooltip: 1
     hideControls: false
   ```

1. **Define Configuration Validation**

   ```yaml
   # Configuration validation
   required_fields:
     - editable
     - graphTooltip
     - style
     - timezone
   
   forbidden_patterns:
     - hardcoded URLs (use variables)
     - absolute paths (use relative)
   ```

### Phase 2: Update Configurations (2 days)

1. **Standardize pluginVersion**

   ```json
   // Update all panels to 12.2.0
   {
     "pluginVersion": "12.2.0"
   }
   ```

1. **Set Style Configuration**

   ```json
   // Add to all dashboards
   {
     "style": "dark"
   }
   ```

1. **Standardize Base Settings**

   ```json
   // Apply base settings
   {
     "editable": true,
     "graphTooltip": 1,
     "hideControls": false
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

### Phase 3: Create Validation Tool (1 day)

1. **Create Configuration Validator**

   ```python
   # scripts/validate_dashboard_config.py
   def validate_dashboard_config(dashboard_path):
       """Validate dashboard configuration against standards."""
       # Check pluginVersion consistency
       # Check required fields
       # Check for forbidden patterns
   ```

1. **Run Validation**

   ```bash
   # Validate all dashboards
   python scripts/validate_dashboard_config.py grafana/dashboards/*.json
   ```

1. **Document Configuration Standards**

   ```markdown
   # docs/05-operations/grafana-configuration-standards.md
   ## Dashboard Configuration Standards
   
   All dashboards must follow configuration standards...
   ```

## ✅ Success Criteria

- [ ] All panels use pluginVersion 12.2.0 - CURRENT STATE: Mixed versions (9.5.0, 10.4.0, 12.2.0) across dashboards
- [ ] All dashboards have explicit style setting
- [ ] Base settings standardized
- [ ] Configuration validator created
- [ ] All dashboards pass validation
- [ ] Configuration standards documented

## 📊 Verification Commands

```bash
# Verify plugin versions
grep "pluginVersion" grafana/dashboards/*.json | sort -u

# Check style settings
grep "style" grafana/dashboards/*.json

# Run configuration validator
python scripts/validate_dashboard_config.py grafana/dashboards/*.json

# Validate JSON syntax
python -m json.tool grafana/dashboards/*.json > /dev/null
```

## 📈 Impact Assessment

### Positive Impacts

- **Consistency**: Uniform technical configuration
- **Maintainability**: Easier to maintain dashboards
- **Quality**: Automated validation prevents drift
- **Technical Debt**: Reduced configuration inconsistencies

### Potential Risks

- **Plugin Upgrade**: May introduce breaking changes
- **Compatibility**: Some panels may not work with new version
- **Maintenance**: Validator needs ongoing updates

### Mitigation Strategies

- **Testing**: Test plugin upgrade in staging
- **Gradual Rollout**: Upgrade dashboards incrementally
- **Fallback**: Keep backup of previous versions
- **Monitoring**: Watch for issues after upgrade

## 🎯 Related Issues

- **Depends On**: DASH-009 (Metadata)
- **Related To**: All DASH-* issues

## ⏳ Time Estimate

**Total**: 4 days
**Start Date**: 2026-05-08
**Target Completion**: 2026-05-14

## 👥 Assignee

(TBD - comment on tracking issue to claim)

## 📋 Checklist

- [x] pluginVersion standard defined
- [x] Style standard established
- [x] Configuration validation rules defined
- [ ] All pluginVersions updated to 12.2.0 - CURRENT STATE: Mixed versions across dashboards
- [ ] All dashboards have explicit style
- [ ] Base settings standardized
- [ ] Configuration validator created
- [ ] All dashboards validated
- [ ] Configuration standards documented
- [ ] Changes tested in staging

### Current Implementation Status

**Completed:**
- pluginVersion standard defined (target: 12.2.0)
- Style standard established (dark mode, explicit settings)
- Configuration validation rules defined (required fields, forbidden patterns)

**Current pluginVersion State:**
- bioetl-control-plane-v1.json: 9.5.0 (21 instances) - needs upgrade
- bioetl-dq-v2.json: Mixed 10.4.0 (1 instance) and 12.2.0 (1 instance) - needs standardization to 12.2.0
- bioetl-runtime.json: Mixed 10.4.0 (3 instances) and 12.2.0 (2 instances) - needs standardization to 12.2.0
- bioetl-provider-health-v2.json: Mixed 10.4.0 (3 instances) and 12.2.0 (2 instances) - needs standardization to 12.2.0
- bioetl-overview-v2.json: TBD - needs review
- bioetl-workflow-overview.json: TBD - needs review
- bioetl-silver-reject-explorer.json: TBD - needs review

**Current style State:**
- Not all dashboards explicitly set style - needs verification and addition

**Remaining:**
- Upgrade control-plane-v1 from 9.5.0 to 12.2.0 (21 instances)
- Standardize dq-v2 to 12.2.0 (upgrade 1 instance from 10.4.0)
- Standardize runtime to 12.2.0 (upgrade 3 instances from 10.4.0)
- Standardize provider-health-v2 to 12.2.0 (upgrade 3 instances from 10.4.0)
- Review and standardize overview-v2, workflow-overview, silver-reject-explorer
- Add explicit style configuration to all dashboards
- Standardize base settings (editable, graphTooltip, hideControls)
- Create configuration validator script
- Run validation on all dashboards
- Document configuration standards
- Test plugin upgrade in staging

## 🎯 Notes

This issue reduces technical debt by establishing consistent technical configurations across all dashboards. The validator should be run as part of the dashboard development process.
