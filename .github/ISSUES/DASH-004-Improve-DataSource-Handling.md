# Improve DataSource Integration and Health Monitoring

**Status**: Open
**Priority**: P2 (Medium)
**Labels**: `dashboard`, `datasource`, `integration`, `reliability`
**Epic**: Grafana Dashboard Improvements 2026Q2

## 🎯 Problem

Current dashboards use different datasource approaches (Prometheus vs Quarantine Explorer) with inconsistent handling. There are no explicit datasource health indicators, making it difficult to distinguish between missing data and datasource failures.

## 🔍 Root Cause Analysis

1. **Mixed Datasource Approaches**: Most dashboards use Prometheus, Silver Reject Explorer uses custom HTTP API
2. **No Health Indicators**: Dashboards don't show datasource health status
3. **Inconsistent Error Handling**: Different dashboards handle datasource errors differently
4. **No Fallback Strategy**: No graceful degradation when datasource unavailable
5. **URL-Based Query Complexity**: Quarantine Explorer uses complex URL-based JSON queries

## 📋 Scope

**Affected Components:**

- `grafana/dashboards/bioetl-silver-reject-explorer.json` (Quarantine Explorer datasource)
- All Prometheus datasource configurations
- Error handling in dashboard panels
- Datasource health monitoring

**Impact Analysis:**

```bash
# Count datasource configurations
grep -rn "datasource" grafana/dashboards/*.json | wc -l
```

## 🎯 Solution Plan

### Phase 1: Define Datasource Standard (1 day)

1. **Establish Datasource Categories**

   ```yaml
   # Datasource categories
   primary:
     - Prometheus (metrics, recording rules)
   
   secondary:
     - Quarantine Explorer (forensic data)
     - Loki (logs)
     - Tempo (traces)
   ```

1. **Define Health Monitoring Requirements**

   ```yaml
   # Datasource health monitoring
   health_indicators:
     Prometheus:
       - scrape_target_status
       - rule_evaluation_health
     Quarantine Explorer:
       - API endpoint availability
       - response time
       - error rate
   ```

1. **Define Error Handling Standards**

   ```yaml
   # Error handling patterns
   error_handling:
     noValue: "UNKNOWN"
     datasource_error: "DATASOURCE_ERROR"
     timeout: "TIMEOUT"
     fallback: show_last_known_state
   ```

### Phase 2: Implement Datasource Health Monitoring (2 days)

1. **Add Prometheus Health Indicator**

   ```json
   // Add to all Prometheus-based dashboards
   {
     "title": "Monitor Datasource Health",
     "targets": [
       {
         "expr": "up{job=\"bioetl\"}"
       }
     ]
   }
   ```

1. **Add Quarantine Explorer Health Indicator**

   ```json
   // Add to Silver Reject Explorer
   {
     "title": "Monitor Quarantine API Health",
     "targets": [
       {
         "url": "/ops/health"
       }
     ]
   }
   ```

1. **Implement Graceful Error Handling**

   ```json
   // Standard error handling configuration
   {
     "fieldConfig": {
       "defaults": {
         "noValue": "DATASOURCE_UNAVAILABLE",
         "mappings": [
           {
             "type": "special",
             "options": {
               "match": "null",
               "result": {
                 "text": "CHECK_DATASOURCE",
                 "color": "gray"
               }
             }
           }
         ]
       }
     }
   }
   ```

### Phase 3: Standardize URL-Based Queries (2 days)

1. **Create Query Utility Functions**

   ```javascript
   // Standardize Quarantine Explorer queries
   function buildQuarantineQuery(basePath, filters) {
     // Build consistent URL-based queries
   }
   ```

1. **Add Query Error Handling**

   ```json
   // Add error handling to URL-based queries
   {
     "targets": [
       {
         "url": "/ops/quarantine/...",
         "errorHandling": "show_error_message"
       }
     ]
   }
   ```

1. **Document Datasource Patterns**

   ```markdown
   # docs/05-operations/grafana-datasource-guide.md
   ## Datasource Integration Patterns
   
   All dashboards must follow datasource standards...
   ```

## ✅ Success Criteria

- [ ] All dashboards include datasource health indicators - CURRENT STATE: No explicit datasource health indicators found
- [ ] Error handling standardized across dashboards - CURRENT STATE: Partially implemented (noValue used in silver-reject-explorer and dq-v2)
- [ ] URL-based queries have consistent error handling
- [ ] Datasource failures clearly distinguished from missing data
- [ ] Health monitoring documented
- [ ] Graceful degradation implemented

## 📊 Verification Commands

```bash
# Check datasource health indicators
grep -rn "datasource.*health\|up{" grafana/dashboards/*.json

# Verify error handling
grep -rn "noValue\|mappings" grafana/dashboards/*.json

# Validate JSON syntax
python -m json.tool grafana/dashboards/*.json > /dev/null
```

## 📈 Impact Assessment

### Positive Impacts

- **Reliability**: Clear datasource health status
- **Debugging**: Easier to identify datasource issues
- **Consistency**: Uniform error handling across dashboards
- **User Experience**: Better feedback when datasources fail

### Potential Risks

- **Complexity**: Additional health monitoring panels
- **Performance**: Extra health checks may impact load
- **Maintenance**: More configuration to manage

### Mitigation Strategies

- **Minimal Overhead**: Use efficient health check queries
- **Consolidated Monitoring**: Reuse health check patterns
- **Documentation**: Clear error messages guide users
- **Testing**: Validate health check performance

## 🎯 Related Issues

- **Depends On**: DASH-001 (Navigation), DASH-002 (Color Scheme)
- **Related To**: DASH-005 (Missing Data Handling)

## ⏳ Time Estimate

**Total**: 5 days
**Start Date**: 2026-05-08
**Target Completion**: 2026-05-15

## 👥 Assignee

(TBD - comment on tracking issue to claim)

## 📋 Checklist

- [x] Datasource standard documented
- [x] Health monitoring requirements defined
- [x] Error handling standards established
- [ ] Prometheus health indicator added to all dashboards - CURRENT STATE: No explicit health indicators found
- [ ] Quarantine Explorer health indicator added - CURRENT STATE: No explicit health indicators found
- [ ] Error handling standardized across dashboards - CURRENT STATE: Partially implemented (noValue used in silver-reject-explorer and dq-v2)
- [ ] URL-based queries standardized
- [ ] Health monitoring documented
- [ ] Changes deployed to staging
- [ ] Error handling tested

### Current Implementation Status

**Completed:**
- Datasource standard defined (primary: Prometheus, secondary: Quarantine Explorer/Loki/Tempo)
- Health monitoring requirements defined (scrape_target_status, rule_evaluation_health, API endpoint availability)
- Error handling standards defined (noValue: UNKNOWN, datasource_error: DATASOURCE_ERROR, timeout: TIMEOUT)

**Current State Analysis:**
- bioetl-silver-reject-explorer.json: Uses noValue with descriptive messages for various panels (e.g., "No Silver reject count returned for current filters. Verify Quarantine Explorer before treating this as OK.")
- bioetl-dq-v2.json: Uses noValue: "UNKNOWN" for multiple panels
- Other dashboards: Use "-- Grafana --" and Prometheus datasources, but no explicit datasource health indicators found
- No explicit DATASOURCE_UNAVAILABLE or CHECK_DATASOURCE status indicators found
- No Prometheus health indicator panels (up{job="bioetl"}) found in dashboards

**Remaining:**
- Add Prometheus health indicator panels to all Prometheus-based dashboards
- Add Quarantine Explorer health indicator to silver-reject-explorer dashboard
- Standardize error handling with DATASOURCE_UNAVAILABLE and CHECK_DATASOURCE mappings
- Implement graceful degradation for datasource failures
- Document datasource patterns in grafana-datasource-guide.md

## 🎯 Notes

This issue improves dashboard reliability by making datasource health visible and handling errors gracefully. The patterns established should be followed in all future dashboard development.
