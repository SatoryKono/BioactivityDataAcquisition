# Unify Color Scheme, Status Mappings, and Thresholds Across All Dashboards

**Status**: Open
**Priority**: P1 (High)
**Labels**: `dashboard`, `visualization`, `consistency`, `UX`
**Epic**: Grafana Dashboard Improvements 2026Q2

## 🎯 Problem

Current dashboards use inconsistent color schemes, status mappings, and threshold configurations. This creates confusion for operators interpreting dashboard states and makes it difficult to maintain consistent visual language across the observability stack.

## 🔍 Root Cause Analysis

1. **Inconsistent Status Mappings**: Different dashboards use different text/color mappings for OK/WARN/CRIT/UNKNOWN
2. **Threshold Variance**: Similar metrics use different threshold values across dashboards
3. **Color Mode Inconsistency**: Some panels use background color, others use value color
4. **UNKNOWN Semantics**: Different interpretations of UNKNOWN state (missing data vs healthy state)
5. **Threshold Configuration**: Different threshold step configurations for similar metrics

## 📋 Scope

**Affected Components:**

- All dashboard JSON files in `grafana/dashboards/`
- All stat/gauge panels with status indicators
- All threshold configurations
- All color mode settings

**Impact Analysis:**

```bash
# Count threshold inconsistencies
grep -rn "thresholds" grafana/dashboards/*.json | wc -l

# Count status mapping inconsistencies
grep -rn "mappings" grafana/dashboards/*.json | wc -l
```

## 🎯 Solution Plan

### Phase 1: Define Color and Status Standard (1 day)

1. **Establish Standard Status Mappings**

   ```yaml
   # Standard status mappings
   status:
     OK:
       value: 0
       color: green
       text: "OK"
     WARN:
       value: 1
       color: orange
       text: "WARN"
     CRIT:
       value: 2
       color: red
       text: "CRIT"
     UNKNOWN:
       value: null
       color: gray
       text: "UNKNOWN"
   ```

1. **Define Standard Threshold Values**

   ```yaml
   # Standard thresholds for common metrics
   error_rate:
     warn: 0.05  # 5%
     crit: 0.20  # 20%
   
   quality_score:
     warn: 0.80  # 80%
     crit: 0.95  # 95%
   
   latency:
     warn: 300   # 5 minutes
     crit: 900   # 15 minutes
   ```

1. **Define Color Mode Rules**

   ```yaml
   # Standard color mode usage
   stat_panels:
     current_status: background
     trend_metrics: value
   
   gauge_panels:
     current_status: background
     rate_metrics: value
   
   table_panels:
     status_columns: color-background
   ```

### Phase 2: Update All Dashboards (3 days)

1. **Update Status Mappings in All Panels**

   ```json
   // Standard status mapping configuration
   {
     "mappings": [
       {
         "type": "value",
         "options": {
           "0": {"text": "OK", "color": "green"},
           "1": {"text": "WARN", "color": "orange"},
           "2": {"text": "CRIT", "color": "red"}
         }
       },
       {
         "type": "special",
         "options": {
           "match": "null",
           "result": {"text": "UNKNOWN", "color": "gray"}
         }
       }
     ]
   }
   ```

1. **Standardize Threshold Configurations**

   ```json
   // Standard threshold configuration
   {
     "thresholds": {
       "mode": "absolute",
       "steps": [
         {"color": "green", "value": null},
         {"color": "orange", "value": 1},
         {"color": "red", "value": 2}
       ]
     }
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

### Phase 3: Validation and Documentation (1 day)

1. **Validate Visual Consistency**

   ```bash
   # Manual verification
   - Check all stat panels use consistent status colors
   - Verify threshold values match standard
   - Confirm color mode usage follows rules
   ```

1. **Document Standards**

   ```markdown
   # docs/05-operations/grafana-dashboard-standards.md
   ## Color Scheme and Status Standards
   
   All dashboards must follow the standard status mappings...
   ```

## ✅ Success Criteria

- [ ] All status mappings use standard OK/WARN/CRIT/UNKNOWN values
- [ ] All threshold values standardized for similar metrics
- [ ] Color mode usage follows defined rules
- [ ] UNKNOWN semantics documented and consistent
- [ ] Visual consistency across all dashboards
- [ ] Standards documented

## 📊 Verification Commands

```bash
# Verify status mapping consistency
grep -A 10 "mappings" grafana/dashboards/*.json

# Check threshold configurations
grep -A 5 "thresholds" grafana/dashboards/*.json

# Validate JSON syntax
python -m json.tool grafana/dashboards/*.json > /dev/null
```

## 📈 Impact Assessment

### Positive Impacts

- **Consistency**: Uniform visual language across all dashboards
- **Usability**: Operators can interpret status consistently
- **Maintainability**: Standard thresholds easier to maintain
- **Reduced Errors**: Less confusion about status meanings

### Potential Risks

- **Breaking Changes**: Users accustomed to current colors/thresholds
- **Metric Specificity**: Some metrics may require custom thresholds
- **Testing Overhead**: Visual verification required

### Mitigation Strategies

- **Documentation**: Clearly document new standards
- **Gradual Rollout**: Deploy to staging first
- **User Communication**: Announce changes before deployment
- **Exceptions**: Document justified threshold exceptions

## 🎯 Related Issues

- **Depends On**: DASH-001 (Navigation)
- **Blocks**: DASH-005 (Missing Data Handling)
- **Related To**: All DASH-* issues

## ⏳ Time Estimate

**Total**: 5 days
**Start Date**: 2026-05-08
**Target Completion**: 2026-05-15

## 👥 Assignee

(TBD - comment on tracking issue to claim)

## 📋 Checklist

- [ ] Color and status standard documented
- [ ] Threshold values standardized
- [ ] Color mode rules defined
- [ ] All dashboard status mappings updated
- [ ] All dashboard thresholds updated
- [ ] Visual consistency verified
- [ ] Documentation created
- [ ] Changes deployed to staging
- [ ] User communication sent

## 🎯 Notes

This issue establishes the visual language standard for all Grafana dashboards. The standard should be referenced in all future dashboard development and included in the dashboard guide.
