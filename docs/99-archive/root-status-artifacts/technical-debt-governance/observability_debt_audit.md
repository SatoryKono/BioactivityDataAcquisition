# Observability Debt Audit: DQ Logging and Metrics

**Date:** 2026-01-25
**Scope:** Application layer DQ analyzers and logging coverage
**Status:** Completed

## Executive Summary

This audit identified **16 observability debt items** across the Data Quality (DQ) analysis layer, with **4 critical** and **10 high** priority issues. The primary deficiency is the lack of logging for critical DQ operations and decisions across Bronze, Silver, and Gold layers.

### Severity Breakdown
- **Critical:** 4 items
- **High:** 10 items
- **Medium:** 2 items
- **Total:** 16 items

## Detailed Findings

### Critical Issues

| Component | File | Issue | Impact |
|-----------|------|-------|--------|
| Silver Statistics Helpers | `src/bioetl/application/services/dq/silver_statistics_helpers.py` | Schema drift detection not logged (`check_schema_drift_stats()`) | Undetected schema changes can cause data pipeline failures |
| Silver Statistics Helpers | `src/bioetl/application/services/dq/silver_statistics_helpers.py` | Type conformance violations not logged (`check_type_conformance_stats()`) | Mixed-type columns can cause downstream processing errors |
| Gold Checks Integrity | `src/bioetl/application/services/dq/_checks_integrity.py` | Orphan references not logged (`check_referential_integrity()`) | Broken FK relationships can cause data integrity issues |
| Silver Statistics Helpers | `src/bioetl/application/services/dq/silver_statistics_helpers.py` | Content hash collisions not logged (`check_content_hash_integrity_stats()`) | Hash collisions can indicate data corruption or deduplication issues |

### High Priority Issues

| Component | File | Issue | Impact |
|-----------|------|-------|--------|
| DataQualityService | `src/bioetl/application/services/data_quality_service.py` | Insufficient logging in `evaluate()` method | No visibility into DQ evaluation results across layers |
| BronzeDQAnalyzer | `src/bioetl/application/services/dq/bronze_analyzer.py` | No logging for individual validation checks | Cannot debug Bronze layer DQ issues |
| SilverDQAnalyzer | `src/bioetl/application/services/dq/silver_analyzer.py` | No logging of orchestration events | Cannot trace Silver DQ check execution |
| SilverCheckExecutor | `src/bioetl/application/services/dq/silver_check_executor.py` | No logging of individual check outcomes | Cannot identify which Silver checks failed |
| SilverThresholdChecker | `src/bioetl/application/services/dq/silver_threshold.py` | No logging of threshold breaches | Cannot detect when metrics exceed thresholds |
| GoldDQAnalyzer | `src/bioetl/application/services/dq/gold_analyzer.py` | No logging of check execution | Cannot trace Gold DQ check execution |
| Gold Checks Basic | `src/bioetl/application/services/dq/_checks_basic.py` | No logging of record count, completeness, freshness violations | Cannot detect Gold data quality violations |
| Gold Checks Business | `src/bioetl/application/services/dq/_checks_business.py` | No logging of rule violations | Cannot identify which business rules failed |
| Gold Checks Statistical | `src/bioetl/application/services/dq/_checks_statistical.py` | No logging of anomaly detection | Cannot detect data anomalies in Gold layer |
| Silver Statistics Helpers | `src/bioetl/application/services/dq/silver_statistics_helpers.py` | No logging of uniqueness violations | Cannot detect duplicate records |

### Medium Priority Issues

| Component | File | Issue | Impact |
|-----------|------|-------|--------|
| SilverStatisticsCalculator | `src/bioetl/application/services/dq/silver_statistics.py` | No logging of individual calculations | Limited visibility into metric computation |
| SilverStatisticsCalculator | `src/bioetl/application/services/dq/silver_statistics.py` | Stateless design defers logging to orchestrators | Relies on orchestrators for logging coverage |

### Adequate Logging (No Action Needed)

| Component | File | Assessment |
|-----------|------|------------|
| ConfigDQService | `src/bioetl/application/services/config_dq_service.py` | Logging for successful config validation - adequate |
| DQReportService | `src/bioetl/application/services/dq_report_service.py` | Logs start (debug) and result (info) - adequate |
| DQReportWriter | `src/bioetl/infrastructure/export/dq_report_writer.py` | Logs info-level message upon successful report writing - adequate |
| DQReportBuilders | `src/bioetl/application/services/dq/dq_report_builders.py` | Utility module for serialization - no logging expected |

## Recommendations

### Immediate Actions (Critical)

1. **Add schema drift logging in Silver layer**
   - File: `src/bioetl/application/services/dq/silver_statistics_helpers.py`
   - Function: `check_schema_drift_stats()`
   - Log level: WARN/INFO
   - Content: new_fields, missing_fields, type_changes

2. **Add type conformance logging in Silver layer**
   - File: `src/bioetl/application/services/dq/silver_statistics_helpers.py`
   - Function: `check_type_conformance_stats()`
   - Log level: WARN
   - Content: columns with mixed types

3. **Add orphan reference logging in Gold layer**
   - File: `src/bioetl/application/services/dq/_checks_integrity.py`
   - Function: `check_referential_integrity()`
   - Log level: WARN/ERROR
   - Content: orphan record counts, FK violations

4. **Add content hash collision logging in Silver layer**
   - File: `src/bioetl/application/services/dq/silver_statistics_helpers.py`
   - Function: `check_content_hash_integrity_stats()`
   - Log level: WARN
   - Content: collision count, records checked

### Short-Term Actions (High Priority)

1. **Add DQ evaluation result logging in DataQualityService**
   - File: `src/bioetl/application/services/data_quality_service.py`
   - Method: `evaluate()`
   - Log level: INFO
   - Content: layer, check status, failures

2. **Add validation check logging in BronzeDQAnalyzer**
   - File: `src/bioetl/application/services/dq/bronze_analyzer.py`
   - Log level: DEBUG/INFO
   - Content: each validation check and result

3. **Add orchestration logging in SilverDQAnalyzer**
   - File: `src/bioetl/application/services/dq/silver_analyzer.py`
   - Log level: DEBUG/INFO
   - Content: check execution events, results

4. **Add check outcome logging in SilverCheckExecutor**
   - File: `src/bioetl/application/services/dq/silver_check_executor.py`
   - Log level: INFO
   - Content: each check execution and result

5. **Add threshold breach logging in SilverThresholdChecker**
   - File: `src/bioetl/application/services/dq/silver_threshold.py`
   - Log level: WARN
   - Content: threshold violations, metric values

6. **Add check execution logging in GoldDQAnalyzer**
   - File: `src/bioetl/application/services/dq/gold_analyzer.py`
   - Log level: DEBUG/INFO
   - Content: check execution events, results

7. **Add basic check logging in Gold layer**
   - File: `src/bioetl/application/services/dq/_checks_basic.py`
   - Functions: `check_record_count()`, `check_completeness()`, `check_data_freshness()`
   - Log level: WARN/ERROR
   - Content: threshold breaches, failures

8. **Add business rule logging in Gold layer**
   - File: `src/bioetl/application/services/dq/_checks_business.py`
   - Function: `check_business_rules()`
   - Log level: WARN/ERROR
   - Content: rule violations, reject reasons

9. **Add anomaly detection logging in Gold layer**
   - File: `src/bioetl/application/services/dq/_checks_statistical.py`
   - Function: `check_anomaly_detection()`
   - Log level: WARN
   - Content: detected anomalies, statistical profile violations

10. **Add uniqueness violation logging in Silver layer**
    - File: `src/bioetl/application/services/dq/silver_statistics_helpers.py`
    - Function: `check_uniqueness_stats()`
    - Log level: WARN
    - Content: duplicate count, duplicate rate

## Architecture Considerations

### Logging Strategy

The current design pattern in DQ analyzers is:
- Helper functions return result objects with status
- Orchestrators consume results and aggregate
- Logging is deferred to higher-level services

This pattern has trade-offs:
- **Pros:** Separation of concerns, testability, reusability
- **Cons:** Limited visibility into individual check execution

**Recommendation:** Add strategic logging at both levels:
- Helper functions: Log critical violations (schema drift, orphan references, threshold breaches)
- Orchestrators: Log check execution events and aggregated results

### Logging Levels

- **DEBUG:** Check execution start/end, detailed metrics
- **INFO:** Check results, summary statistics
- **WARN:** Threshold breaches, violations, anomalies
- **ERROR:** Critical failures, integrity issues

## Related Files

### DQ Analyzer Modules
- `src/bioetl/application/services/data_quality_service.py`
- `src/bioetl/application/services/config_dq_service.py`
- `src/bioetl/application/services/dq_report_service.py`
- `src/bioetl/application/services/dq/bronze_analyzer.py`
- `src/bioetl/application/services/dq/silver_analyzer.py`
- `src/bioetl/application/services/dq/silver_check_executor.py`
- `src/bioetl/application/services/dq/silver_statistics.py`
- `src/bioetl/application/services/dq/silver_threshold.py`
- `src/bioetl/application/services/dq/silver_statistics_helpers.py`
- `src/bioetl/application/services/dq/gold_analyzer.py`
- `src/bioetl/application/services/dq/_checks_basic.py`
- `src/bioetl/application/services/dq/_checks_business.py`
- `src/bioetl/application/services/dq/_checks_integrity.py`
- `src/bioetl/application/services/dq/_checks_statistical.py`
- `src/bioetl/application/services/dq/dq_report_builders.py`

### Infrastructure
- `src/bioetl/infrastructure/export/dq_report_writer.py`

## Conclusion

The DQ layer has significant observability debt, particularly in helper functions that perform critical checks (schema drift, integrity violations, anomaly detection) without logging. Addressing these issues will improve debugging capabilities, enable faster incident response, and provide better visibility into data quality across the pipeline.

**Next Steps:**
1. Prioritize critical issues for immediate remediation
2. Create logging standards for DQ operations
3. Implement logging enhancements in phases
4. Validate logging coverage with integration tests
