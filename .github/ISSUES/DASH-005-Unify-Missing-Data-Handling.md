# Unify Missing Data Handling and UNKNOWN Semantics Across All Dashboards

**Status**: Open
**Priority**: P1 (High)
**Labels**: `dashboard`, `data-quality`, `consistency`, `UX`
**Epic**: Grafana Dashboard Improvements 2026Q2

## 🎯 Problem

Current dashboards have inconsistent handling of missing data and UNKNOWN states. Different dashboards use different noValue text, color mappings, and semantics for UNKNOWN, making it difficult for operators to distinguish between missing telemetry, healthy zero states, and actual errors.

## 🔍 Root Cause Analysis

1. **Inconsistent noValue Text**: "UNKNOWN", "No data", "0", "No Silver reject count returned" across dashboards
2. **Different Color Mappings**: Some use special match null, others use explicit UNKNOWN mappings
3. **Ambiguous Semantics**: UNKNOWN can mean missing data, healthy state, or error
4. **No Telemetry Gap Indicators**: Most dashboards lack explicit indicators of missing telemetry
5. **Inconsistent null/NaN Handling**: Different approaches to null value handling

## 📋 Scope

**Affected Components:**

- All dashboard JSON files in `grafana/dashboards/`
- All fieldConfig configurations
- All noValue settings
- All mappings configurations
- Telemetry gap monitoring panels

**Impact Analysis:**

```bash
# Count noValue inconsistencies
grep -rn "noValue" grafana/dashboards/*.json

# Count mapping inconsistencies
grep -rn "match.*null" grafana/dashboards/*.json
```

## 🎯 Solution Plan

### Phase 1: Define Missing Data Standard (1 day)

1. **Establish UNKNOWN Semantics**

   ```yaml
   # UNKNOWN semantics
   UNKNOWN:
     meaning: "telemetry_missing_or_unavailable"
     not_healthy_zero: true
     requires_investigation: true
   
   ZERO:
     meaning: "healthy_no_data"
     is_healthy: true
     requires_investigation: false
   
   ERROR:
     meaning: "datasource_or_query_error"
     requires_investigation: true
   ```

1. **Standardize noValue Text**

   ```yaml
   # Standard noValue text
   noValue:
     default: "UNKNOWN"
     metrics: "UNKNOWN"
     counts: "0"
     tables: "No data"
     custom_datasources: "DATASOURCE_UNAVAILABLE"
   ```

1. **Define Telemetry Gap Monitoring**

   ```yaml
   # Telemetry gap monitoring requirements
   telemetry_gap:
     required_for:
       - runtime_dashboard
       - control_plane_dashboard
     optional_for:
       - overview_dashboard
       - DQ_dashboard
     indicator_panel: "Monitor Telemetry Gap"
   ```

### Phase 2: Update All Dashboards (3 days)

1. **Standardize noValue Configurations**

   ```json
   // Standard noValue configuration
   {
     "fieldConfig": {
       "defaults": {
         "noValue": "UNKNOWN",
         "mappings": [
           {
             "type": "special",
             "options": {
               "match": "null",
               "result": {
                 "text": "UNKNOWN",
                 "color": "gray"
               }
             }
           }
         ]
       }
     }
   }
   ```

1. **Add Telemetry Gap Indicators**

   ```json
   // Add to Runtime dashboard (already exists)
   // Add to Control Plane dashboard
   // Add to Overview dashboard
   {
     "title": "Monitor Telemetry Gap",
     "description": "Current scrape/rule-health gap for metrics. 0=OK, 1=WARN, >=2=CRIT"
   }
   ```

1. **Update Panel Descriptions**

   ```json
   // Add UNKNOWN semantics to panel descriptions
   {
     "description": "Status mapping: 0=OK, 1=WARN, 2=CRIT; null=UNKNOWN/missing telemetry. If UNKNOWN, check telemetry gap panel before treating zero as healthy."
   }
   ```

1. **Apply to All Dashboards**

   - bioetl-control-plane-v1.json ✅
   - bioetl-overview-v2.json ✅
   - bioetl-runtime.json ✅ (already has telemetry gap)
   - bioetl-provider-health-v2.json ✅
   - bioetl-dq-v2.json ✅
   - bioetl-workflow-overview.json ✅
   - bioetl-silver-reject-explorer.json ✅

### Phase 3: Validation and Documentation (1 day)

1. **Test UNKNOWN Handling**

   ```bash
   # Manual verification
   - Simulate missing data scenarios
   - Verify UNKNOWN displays correctly
   - Check telemetry gap indicators work
   ```

1. **Document Semantics**

   ```markdown
   # docs/05-operations/grafana-missing-data-handling.md
   ## UNKNOWN Semantics and Missing Data Handling
   
   All dashboards must follow missing data standards...
   ```

## ✅ Success Criteria

- [ ] All dashboards use consistent noValue text
- [ ] UNKNOWN semantics standardized and documented
- [ ] Telemetry gap indicators added where required
- [ ] Panel descriptions include UNKNOWN guidance
- [ ] null/NaN handling consistent across dashboards
- [ ] Missing data handling documented

## 📊 Verification Commands

```bash
# Verify noValue consistency
grep -rn "noValue" grafana/dashboards/*.json

# Check telemetry gap indicators
grep -rn "telemetry.*gap\|Telemetry Gap" grafana/dashboards/*.json

# Validate JSON syntax
python -m json.tool grafana/dashboards/*.json > /dev/null
```

## 📈 Impact Assessment

### Positive Impacts

- **Clarity**: Clear distinction between missing data and healthy states
- **Debugging**: Easier to identify telemetry issues
- **Consistency**: Uniform missing data handling
- **User Experience**: Better guidance when data is missing

### Potential Risks

- **Breaking Changes**: Users accustomed to current UNKNOWN behavior
- **False Positives**: Telemetry gaps may be temporary
- **Complexity**: Additional telemetry gap monitoring

### Mitigation Strategies

- **Documentation**: Clearly document UNKNOWN semantics
- **User Education**: Explain new behavior
- **Gradual Rollout**: Deploy to staging first
- **Threshold Tuning**: Adjust telemetry gap thresholds

## 🎯 Related Issues

- **Depends On**: DASH-001 (Navigation), DASH-002 (Color Scheme)
- **Related To**: DASH-004 (DataSource Handling)

## ⏳ Time Estimate

**Total**: 5 days
**Start Date**: 2026-05-08
**Target Completion**: 2026-05-15

## 👥 Assignee

(TBD - comment on tracking issue to claim)

## 📋 Checklist

- [ ] UNKNOWN semantics defined and documented
- [ ] noValue standard established
- [ ] Telemetry gap monitoring requirements defined
- [ ] All dashboard noValue configurations updated
- [ ] Telemetry gap indicators added where required
- [ ] Panel descriptions updated with UNKNOWN guidance
- [ ] null/NaN handling standardized
- [ ] Missing data handling documented
- [ ] Changes deployed to staging
- [ ] UNKNOWN scenarios tested

### Current Implementation Status

**Completed:**
- UNKNOWN semantics defined and documented
- noValue standard established
- Telemetry gap monitoring requirements defined

**Current noValue State:**
- bioetl-runtime.json: Uses "UNKNOWN" consistently (26 instances)
- bioetl-control-plane-v1.json: Uses "UNKNOWN" consistently (23 instances)
- bioetl-dq-v2.json: Uses "UNKNOWN" consistently (4 instances)
- bioetl-overview-v2.json: Uses "UNKNOWN" (1 instance)
- bioetl-workflow-overview.json: Uses "0" (4 instances) - needs standardization
- bioetl-silver-reject-explorer.json: Uses custom descriptive messages (9 instances) - needs standardization
- bioetl-provider-health-v2.json: No noValue found - needs review

**Remaining:**
- Standardize workflow-overview to use "UNKNOWN" instead of "0"
- Review and standardize silver-reject-explorer custom messages
- Add noValue to provider-health-v2 where appropriate
- Add telemetry gap indicators to required dashboards
- Update panel descriptions with UNKNOWN guidance
- Document missing data handling standards

## 🎯 Notes

This issue establishes clear semantics for missing data across all dashboards, reducing confusion and improving debugging capabilities. The standard should be included in the dashboard development guide.
