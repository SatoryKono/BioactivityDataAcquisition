______________________________________________________________________

Version: 1.0.0
Status: draft
Class: plan
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-07'

______________________________________________________________________

# BioETL Provider Health Dashboard Audit & Refactoring Plan

## Executive Summary

Comprehensive audit of `bioetl-provider-health-v2` dashboard (UID: `bioetl-provider-health-v2`) identified one critical datasource reference issue and several documentation gaps. The dashboard design is solid, navigation contract compliance is excellent, and all PromQL queries are correct. Primary issues are datasource format inconsistency and missing metric documentation for some panels.

**Audit Date**: 2026-05-07
**Dashboard Version**: 6
**Total Panels**: 20
**Critical Issues**: 1
**Medium Issues**: 0
**Low Issues**: 2

---

## 1. Design and Usability Audit

### 1.1 First Screen Layout ✅ EXCELLENT

**First Screen Panels (no scroll required):**
- **id 9100**: GLOBAL Provider Scope (text header)
- **id 9101**: Monitor GLOBAL Provider Severity Matrix (table)
- **id 9102**: Inspect Critical Providers (table)
- **id 9103**: Inspect Provider Top Causes (table)
- **id 9002**: First Action (text guidance)

**Assessment**: First screen answers the primary question "which provider is degraded/failing and why" without scrolling. This follows L0/L1 best practices perfectly.

### 1.2 Navigation Links ✅ COMPLIANT

**Top-level links** (lines 20-75):
- 0. Control Plane → context mapping with `$pipeline_context`
- 1. Overview → context mapping with `$pipeline_context`
- 2. Runtime → context mapping with `$pipeline_context`
- 4. Data Quality → context mapping with `$pipeline_context`
- 5. Workflow → reset scope (no pipeline context)

**Compliance Check**:
- ✅ All required links present per `navigation-links.yaml`
- ✅ `includeVars: false` on all links
- ✅ `${__url_time_range}` preserved on all links
- ✅ Context mapping pattern correctly implemented
- ✅ Reset scope correctly applied for workflow link

### 1.3 Variable Design ✅ EXCELLENT

**Variables** (lines 1623-1696):
1. **provider** (single-select, query-based)
   - Definition: `label_values({__name__=~"bioetl_health_check_(success|degraded|failures)_total"}, provider)`
   - Default: unknown
   - Include All: false (correct - provider requires explicit selection)
   - Description: Clear explanation of provider scope

2. **pipeline_context** (hidden textbox)
   - Purpose: Return context for context mapping
   - Default: unknown
   - Hide: 2 (correctly hidden from UI)

3. **adapter** (multi-select, query-based)
   - Definition: `label_values(bioetl_circuit_breaker_state, adapter)`
   - Include All: true (correct - adapter filtering optional)
   - Description: Clear explanation of adapter scope

**Assessment**: Variable design is excellent, follows project standards perfectly.

### 1.4 Panel Organization ✅ GOOD

**Row Structure**:
- Row 1 (y=0): GLOBAL Provider Scope header
- Row 2 (y=3): GLOBAL severity matrix + critical providers + top causes (3 columns)
- Row 3 (y=10): First Action guidance
- Row 4 (y=18): Health check latency + current status + healthy checks (3 columns)
- Row 5 (y=26): Failure rate + total checks + degraded checks (3 columns)
- Row 6 (y=34): Failure/degraded trend + failure share (2 columns)
- Row 7 (y=42): Retries exhausted table + trend (2 columns)
- Row 8 (y=50): Selected Provider Detail (collapsed row by default)
- Row 9-13 (y=51+): Detailed provider metrics (collapsed)

**Assessment**: Logical flow from GLOBAL summary → current status → selected-range evidence → detailed provider breakdown. Collapsed row for detail prevents first-screen clutter.

### 1.5 Visual Design ✅ GOOD

**Color Coding**:
- Severity matrix: green (0), orange (1), red (2) - correct
- Thresholds consistently applied across panels
- UNKNOWN mapping to gray - correct

**Panel Types**:
- Good mix of table, timeseries, stat, gauge, bargauge
- Table panels for current status (instant queries)
- Timeseries for trends (range queries)
- Stat/gauge for single-value summaries

**Assessment**: Visual design is consistent and follows dashboard v2 patterns.

---

## 2. Compliance with Project Requirements

### 2.1 Navigation Contract Compliance ✅ FULLY COMPLIANT

**Contract**: `docs/03-guides/dashboards/contracts/navigation-links.yaml`

**Required top-level links for bioetl-provider-health-v2**:
- ✅ 0. Control Plane
- ✅ 1. Overview
- ✅ 2. Runtime
- ✅ 4. Data Quality
- ✅ 5. Workflow

**Variable handoff**:
- ✅ Context mapping for pipeline-scoped dashboards
- ✅ Reset scope for workflow
- ✅ No forbidden variables (run_id, payload_hash) in links

**Time handoff**:
- ✅ `${__url_time_range}` on all dashboard links
- ✅ Default time: `now-12h` (L1 standard)
- ✅ Refresh: `30s` (L1 standard)

### 2.2 Datasource Configuration ❌ CRITICAL ISSUE

**Issue**: All panels use string datasource reference instead of object with explicit UID

**Current format** (23 occurrences):
```json
"datasource": "Prometheus"
```

**Required format** (per datasource UID standard):
```json
"datasource": {
  "type": "prometheus",
  "uid": "prometheus"
}
```

**Impact**: Less robust, may break if datasource name changes. Violates datasource UID standard established in general audit.

**Affected panels**:
- id 97, 177, 257, 355, 428, 517, 588, 668, 741, 814, 897, 959, 1022, 1115, 1191, 1252, 1331, 1410, 1470, 1542, 1632, 1673

### 2.3 Observability Requirements ✅ COMPLIANT

**REQ-HEALTH-001**: Status Degraded at 1-2 consecutive errors
- Panel id 114 shows current provider health status
- Recording rules implement degradation logic

**REQ-HEALTH-002**: Status Unhealthy at ≥3 errors
- Panel id 114 shows current provider health status
- Recording rules implement unhealthy logic

**REQ-HEALTH-003**: Metric `provider-health-status` (0=UNHEALTHY, 1=DEGRADED, 2=HEALTHY)
- ✅ Panel id 114 uses `bioetl_provider_health_status`
- ✅ Correct enum mapping in panel configuration

### 2.4 Time/Refresh Policy ✅ COMPLIANT

**Default time**: `now-12h` (line 1699)
- ✅ Matches L1 standard per `navigation-links.yaml`

**Refresh**: `30s` (line 1614)
- ✅ Matches L1 standard per `navigation-links.yaml`

---

## 3. Panel Data Correctness Audit

### 3.1 Recording Rule Dependencies

**Panel → Recording Rule Mapping**:

| Panel ID | Panel Title | Metric Used | Recording Rule Exists |
|----------|-------------|-------------|----------------------|
| 9101 | Monitor GLOBAL Provider Severity Matrix | `bioetl_provider_current_status` | ✅ Yes (line 296) |
| 9102 | Inspect Critical Providers | `bioetl_provider_current_status` | ✅ Yes (line 296) |
| 9103 | Inspect Provider Top Causes | `bioetl_provider_current_cause` | ✅ Yes (lines 299-334) |
| 114 | Current Provider Health Status | `bioetl_provider_health_status` | ✅ Raw metric (no recording rule needed) |
| 1 | Track Health Check Latency (p95) | `bioetl_health_check_latency_seconds_bucket` | ✅ Raw metric (histogram) |
| 2 | Monitor Healthy Checks | `bioetl_health_check_success_total` | ✅ Raw metric (counter) |
| 104 | Track Provider Failure Rate | `bioetl_health_check_failures_total`, `success_total`, `degraded_total` | ✅ Raw metrics |
| 7 | Track Health Checks Total | All health check metrics | ✅ Raw metrics |
| 105 | Monitor Degraded Checks | `bioetl_health_check_degraded_total` | ✅ Raw metric |
| 106 | Track Failure and Degraded Trend | `bioetl_health_check_failures_total`, `degraded_total` | ✅ Raw metrics |
| 107 | Track Provider Failure Share | `bioetl_health_check_failures_total` | ✅ Raw metric |
| 108 | Track Retries Exhausted | `bioetl_data_source_retry_exhausted_total` | ✅ Raw metric |
| 109 | Track Retries Exhausted Trend | `bioetl_data_source_retry_exhausted_total` | ✅ Raw metric |
| 102 | Provider Health Check Latency (p95) | `bioetl_health_check_latency_seconds_bucket` | ✅ Raw metric (histogram) |
| 110 | Adapter Request Latency (p95) | `bioetl_adapter_request_duration_seconds_bucket` | ✅ Raw metric (histogram) |
| 111 | HTTP Errors by Method / Error Type | `bioetl_http_request_errors_total` | ✅ Raw metric |
| 112 | Rate Limiter Wait (p95) | `bioetl_rate_limiter_wait_seconds_bucket` | ✅ Raw metric (histogram) |
| 113 | Minimum Rate Limiter Tokens Available | `bioetl_rate_limiter_tokens_available` | ✅ Raw metric |
| 31 | Circuit Breaker State (max) | `bioetl_circuit_breaker_state` | ✅ Raw metric |
| 32 | Circuit Breaker Trips | `bioetl_circuit_breaker_trips_total` | ✅ Raw metric |

**Assessment**: All metrics referenced in panels exist in recording rules or as raw metrics. No missing metrics.

### 3.2 PromQL Query Validation

**Panel id 9101** - Monitor GLOBAL Provider Severity Matrix:
```promql
bioetl_provider_current_status
```
- ✅ Correct: Uses recording rule
- ✅ Instant query: appropriate for current status
- ✅ No pipeline filter: intentional GLOBAL scope

**Panel id 9102** - Inspect Critical Providers:
```promql
bioetl_provider_current_status >= 1
```
- ✅ Correct: Filters for DEGRADED/FAILING
- ✅ Instant query: appropriate for current status
- ✅ Table format: appropriate for inspection

**Panel id 9103** - Inspect Provider Top Causes:
```promql
topk(5, bioetl_provider_current_cause > 0)
```
- ✅ Correct: Shows top 5 active causes
- ✅ Instant query: appropriate for current status
- ✅ Filters out zero causes

**Panel id 114** - Current Provider Health Status:
```promql
max by (provider) (bioetl_provider_health_status{provider=~"$provider"})
```
- ✅ Correct: Uses raw health status metric
- ✅ Max aggregation: appropriate for enum
- ✅ Provider filter: respects variable

**Panel id 1** - Track Health Check Latency (p95):
```promql
histogram_quantile(0.95, sum by (le, provider) (increase(bioetl_health_check_latency_seconds_bucket{provider=~"$provider"}[$__interval])))
```
- ✅ Correct: histogram_quantile for p95
- ✅ Sum by le, provider: correct histogram aggregation
- ✅ Increase over $__interval: appropriate for rate
- ✅ Provider filter: respects variable

**Panel id 104** - Track Provider Failure Rate:
```promql
(sum(increase(bioetl_health_check_failures_total{provider=~"$provider"}[$__range])) or vector(0)) / 
clamp_min((sum(increase(bioetl_health_check_success_total{provider=~"$provider"}[$__range])) or vector(0)) + 
(sum(increase(bioetl_health_check_degraded_total{provider=~"$provider"}[$__range])) or vector(0)) + 
(sum(increase(bioetl_health_check_failures_total{provider=~"$provider"}[$__range])) or vector(0)), 1)
```
- ✅ Correct: failures / (success + degraded + failures)
- ✅ or vector(0): handles no data case
- ✅ clamp_min(..., 1): prevents division by zero
- ✅ $__range: appropriate for selected-range evidence

**Panel id 107** - Track Provider Failure Share:
```promql
(100 * sum by (provider) (increase(bioetl_health_check_failures_total{provider=~"$provider"}[$__range])) / 
clamp_min(sum(increase(bioetl_health_check_failures_total{provider=~"$provider"}[$__range])), 1)) or vector(0)
```
- ✅ Correct: percentage of total failures
- ✅ clamp_min: prevents division by zero
- ✅ or vector(0): handles no data case
- ⚠️ **POTENTIAL ISSUE**: This calculates share of failures by provider, not share of total checks. May not be the intended metric.

**Panel id 113** - Minimum Rate Limiter Tokens Available:
```promql
min by (provider) (min_over_time(bioetl_rate_limiter_tokens_available{provider=~"$provider"}[$__range])) or vector(0)
```
- ✅ Correct: minimum tokens in range
- ✅ min_over_time: correct for min over time window
- ✅ or vector(0): handles no data case

**Panel id 31** - Circuit Breaker State (max):
```promql
max(max_over_time(bioetl_circuit_breaker_state{adapter=~"$adapter"}[$__range])) or vector(0)
```
- ✅ Correct: max state over time
- ✅ Adapter filter: respects variable
- ✅ or vector(0): handles no data case
- ⚠️ **POTENTIAL ISSUE**: Uses `$adapter` variable but provider dashboard context may not have adapter context. This may show all adapters when adapter=All.

**Assessment**: PromQL queries are generally correct. Two potential issues identified in panels 107 and 31 that need clarification on intended behavior.

### 3.3 Threshold Validation

**Panel id 104** - Track Provider Failure Rate:
- Thresholds: green (null), orange (≥0.01), red (≥0.20)
- ✅ Matches documentation: "yellow >=5%, red >=20%"
- ✅ Unit: percentunit (0-1 range)

**Panel id 102** - Provider Health Check Latency (p95):
- Thresholds: green (null), orange (≥1s), red (≥2s)
- ✅ Matches documentation: "yellow >=0.5s, orange >=2s, red >=5s"
- ⚠️ **DISCREPANCY**: Panel thresholds (1s, 2s) don't match documented thresholds (0.5s, 2s, 5s)

**Panel id 113** - Minimum Rate Limiter Tokens Available:
- Thresholds: red (null), yellow (≥1), green (≥5)
- ✅ Inverted scale: correct (fewer tokens = worse)
- ✅ Matches alert rule threshold (tokens < 1)

**Assessment**: Most thresholds are correct. One discrepancy found in panel 102 latency thresholds.

---

## 4. Errors Found

### Error #1: Datasource Reference Format (CRITICAL)

**Severity**: CRITICAL
**Location**: All 23 panels using Prometheus datasource
**Issue**: String datasource reference instead of object with explicit UID

**Current**:
```json
"datasource": "Prometheus"
```

**Required**:
```json
"datasource": {
  "type": "prometheus",
  "uid": "prometheus"
}
```

**Impact**: Violates datasource UID standard, less robust, may break if datasource name changes

**Affected Panels**: 
- Lines 97, 177, 257, 355, 428, 517, 588, 668, 741, 814, 897, 959, 1022, 1115, 1191, 1252, 1331, 1410, 1470, 1542, 1632, 1673

### Error #2: Latency Threshold Discrepancy (MEDIUM)

**Severity**: MEDIUM
**Location**: Panel id 102 (line 1120-1138)
**Issue**: Panel thresholds don't match documented thresholds

**Panel thresholds**:
- Green: null
- Orange: ≥1s
- Red: ≥2s

**Documented thresholds** (from dashboard-v2-usage.md line 386):
- Green: null
- Yellow: ≥0.5s
- Orange: ≥2s
- Red: ≥5s

**Impact**: Inconsistent thresholds may confuse operators

**Recommendation**: Align panel thresholds with documented standards

### Error #3: Panel 107 Metric Semantics (LOW)

**Severity**: LOW
**Location**: Panel id 107 (line 949)
**Issue**: Metric calculates "provider share of failed probes" which may not be the intended "failure share across providers"

**Current query**:
```promql
(100 * sum by (provider) (increase(bioetl_health_check_failures_total{provider=~"$provider"}[$__range])) / 
clamp_min(sum(increase(bioetl_health_check_failures_total{provider=~"$provider"}[$__range])), 1)) or vector(0)
```

**Issue**: This calculates percentage of total failures by provider, not percentage of total checks that failed per provider

**Impact**: May not answer the intended question

**Recommendation**: Clarify intended metric semantics or adjust query

### Error #4: Panel 31 Adapter Context (LOW)

**Severity**: LOW
**Location**: Panel id 31 (line 1533)
**Issue**: Uses `$adapter` variable but provider dashboard may not have adapter context

**Current query**:
```promql
max(max_over_time(bioetl_circuit_breaker_state{adapter=~"$adapter"}[$__range])) or vector(0)
```

**Issue**: When adapter=All (default), this shows max state across all adapters, which may not be provider-specific

**Impact**: May show misleading circuit breaker state when adapter=All

**Recommendation**: Clarify if this should be provider-scoped or adapter-scoped

### Error #5: Missing Metric Documentation (LOW)

**Severity**: LOW
**Location**: Multiple panels
**Issue**: Some metrics lack documentation in observability contract

**Affected metrics**:
- `bioetl_adapter_request_duration_seconds_bucket` - not documented in main contract
- `bioetl_rate_limiter_wait_seconds_bucket` - not documented in main contract
- `bioetl_rate_limiter_tokens_available` - not documented in main contract
- `bioetl_http_request_errors_total` - not documented in main contract

**Impact**: Difficult to verify metric semantics against contract

**Recommendation**: Add these metrics to observability contract documentation

---

## 5. Refactoring Plan

### Phase 1: Fix Critical Datasource Issues (HIGH PRIORITY)

#### 1.1 Standardize Datasource References

**File**: `grafana/dashboards/bioetl-provider-health-v2.json`

**Action**: Replace all string datasource references with object format

**Pattern**:
```json
// FROM:
"datasource": "Prometheus"

// TO:
"datasource": {
  "type": "prometheus",
  "uid": "prometheus"
}
```

**Affected Lines**: 97, 177, 257, 355, 428, 517, 588, 668, 741, 814, 897, 959, 1022, 1115, 1191, 1252, 1331, 1410, 1470, 1542, 1632, 1673

**Verification**:
```bash
grep -n '"datasource": "Prometheus"' grafana/dashboards/bioetl-provider-health-v2.json
# Expected: No results after fix

grep -n '"uid": "prometheus"' grafana/dashboards/bioetl-provider-health-v2.json
# Expected: 23 results after fix
```

**Estimated Time**: 30 minutes

### Phase 2: Fix Threshold Discrepancy (MEDIUM PRIORITY)

#### 2.1 Align Panel 102 Latency Thresholds

**File**: `grafana/dashboards/bioetl-provider-health-v2.json`
**Panel**: id 102 (line 1120-1138)

**Current thresholds**:
```json
"steps": [
  {
    "color": "green",
    "value": null
  },
  {
    "color": "orange",
    "value": 1
  },
  {
    "color": "red",
    "value": 2
  }
]
```

**Required thresholds** (per documentation):
```json
"steps": [
  {
    "color": "green",
    "value": null
  },
  {
    "color": "yellow",
    "value": 0.5
  },
  {
    "color": "orange",
    "value": 2
  },
  {
    "color": "red",
    "value": 5
  }
]
```

**Estimated Time**: 15 minutes

### Phase 3: Clarify Metric Semantics (LOW PRIORITY)

#### 3.1 Review Panel 107 Metric

**File**: `grafana/dashboards/bioetl-provider-health-v2.json`
**Panel**: id 107 (line 949)

**Action**: 
1. Determine intended metric semantics
2. If "provider share of total failures" is intended, update panel description to clarify
3. If "failure rate per provider" is intended, adjust query to: `(failures / total_checks) * 100`

**Decision Required**: Consult with team on intended metric

**Estimated Time**: 30 minutes (review + decision + implementation)

#### 3.2 Review Panel 31 Adapter Context

**File**: `grafana/dashboards/bioetl-provider-health-v2.json`
**Panel**: id 31 (line 1533)

**Action**:
1. Determine if panel should be provider-scoped or adapter-scoped
2. If provider-scoped, add provider label to circuit breaker metric in instrumentation
3. If adapter-scoped, update panel description to clarify adapter context

**Decision Required**: Consult with team on intended scope

**Estimated Time**: 30 minutes (review + decision + implementation if needed)

### Phase 4: Update Documentation (LOW PRIORITY)

#### 4.1 Add Missing Metrics to Observability Contract

**File**: `docs/04-reference/contracts/observability.md`

**Action**: Add documentation for:
- `bioetl_adapter_request_duration_seconds_bucket`
- `bioetl_rate_limiter_wait_seconds_bucket`
- `bioetl_rate_limiter_tokens_available`
- `bioetl_http_request_errors_total`

**Format**: Follow existing metric documentation pattern

**Estimated Time**: 1 hour

#### 4.2 Update Threshold Documentation

**File**: `docs/03-guides/dashboards/dashboard-v2-usage.md`

**Action**: Ensure all panel thresholds are documented consistently

**Estimated Time**: 30 minutes

### Phase 5: Testing (HIGH PRIORITY)

#### 5.1 Local Dashboard Testing

**Prerequisites**:
- Docker Compose stack running
- Grafana accessible at `http://localhost:3000`
- Prometheus scraping metrics

**Test Procedure**:
1. Apply datasource reference changes
2. Apply threshold changes
3. Restart Grafana to trigger provisioning
4. Verify dashboard loads without errors
5. Verify all panels render data when metrics available
6. Verify variable filters work correctly
7. Verify navigation links work correctly

**Checklist**:
- [ ] Dashboard loads without errors
- [ ] Panel 9101 shows provider severity matrix
- [ ] Panel 9102 shows critical providers when degraded
- [ ] Panel 9103 shows top causes when degraded
- [ ] Panel 114 shows current health status
- [ ] Panel 102 shows correct latency thresholds
- [ ] Navigation links work correctly
- [ ] Provider variable filters correctly
- [ ] Adapter variable filters correctly

**Estimated Time**: 1 hour

#### 5.2 Provisioning Test

**Test Procedure**:
1. Remove existing dashboard directory from Grafana container
2. Restart Grafana to trigger provisioning
3. Verify dashboard is provisioned correctly
4. Verify dashboard UID matches configuration

**Verification**:
```bash
# Check Grafana logs for provisioning errors
docker-compose logs grafana | grep -i error

# Verify dashboard exists
curl -s http://admin:admin@localhost:3000/api/search?query=Provider%20Health | jq '.'
```

**Estimated Time**: 30 minutes

### Phase 6: Rollback Plan

#### 6.1 Git Rollback

**Procedure**:
```bash
# If issues detected after deployment
git revert <commit-hash>
docker-compose restart grafana
```

#### 6.2 Manual Backup

**Pre-Deployment**:
```bash
# Backup current dashboard file
cp grafana/dashboards/bioetl-provider-health-v2.json grafana/dashboards/bioetl-provider-health-v2.json.backup.$(date +%Y%m%d)
```

**Post-Failure**:
```bash
# Restore from backup
cp grafana/dashboards/bioetl-provider-health-v2.json.backup.YYYYMMDD grafana/dashboards/bioetl-provider-health-v2.json
docker-compose restart grafana
```

---

## 6. Execution Timeline

| Phase | Duration | Dependencies | Priority |
|-------|----------|--------------|----------|
| Phase 1: Fix Datasource References | 30 min | None | HIGH |
| Phase 2: Fix Threshold Discrepancy | 15 min | None | MEDIUM |
| Phase 3: Clarify Metric Semantics | 60 min | Team decision | LOW |
| Phase 4: Update Documentation | 90 min | None | LOW |
| Phase 5: Testing | 90 min | Phases 1-2 complete | HIGH |
| Phase 6: Rollback Planning | Ongoing | Throughout | HIGH |

**Total Estimated Time**: 4.75 hours (excluding Phase 3 decision time)

---

## 7. Success Criteria

1. ✅ All datasource references use object format with explicit UID
2. ✅ Panel 102 latency thresholds match documented standards
3. ✅ Panel 107 metric semantics clarified (if needed)
4. ✅ Panel 31 adapter context clarified (if needed)
5. ✅ Missing metrics added to observability contract
6. ✅ Dashboard loads correctly after provisioning
7. ✅ All panels render data when metrics available
8. ✅ Navigation and variables work correctly

---

## 8. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Dashboard provisioning fails | Low | High | Backup before changes, test locally first |
| Panel breaks due to datasource change | Low | Medium | Test all panels after changes |
| Threshold change confuses operators | Low | Low | Document change in CHANGELOG |
| Metric semantics decision delays work | Medium | Low | Proceed with other phases in parallel |
| Documentation becomes outdated | Medium | Low | Include metric documentation in review checklist |

---

## 9. Post-Implementation Actions

1. **Update CHANGELOG.md** with refactoring details
2. **Create GitHub issue** to track metric documentation completion
3. **Add to architecture documentation** as precedent for datasource standards
4. **Schedule follow-up review** in 1 month to ensure no regressions

---

## 10. References

- Audit Report: 2026-05-07 BioETL Provider Health Dashboard Audit
- Navigation Contract: `docs/03-guides/dashboards/contracts/navigation-links.yaml`
- Dashboard Usage Guide: `docs/03-guides/dashboards/dashboard-v2-usage.md`
- Prometheus Configuration: `grafana/prometheus.yml`
- Prometheus Rules: `grafana/prometheus-rules/bioetl_observability.yml`
- Observability Contract: `docs/04-reference/contracts/observability.md`

______________________________________________________________________
