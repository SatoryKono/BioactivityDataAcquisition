# BioETL Test Swarm Final Report

**Task ID**: SWARM-001
**Дата**: 2026-04-17 09:29
**Mode**: full_audit
**Duration**: 15m 32s
**Overall Status**: 🟡 YELLOW
**Agent Tree**: L1 → 5×L2 → 5×L3 (total: 11 agents)

## Executive Summary
Test execution completed successfully across all architectural layers. Overall test coverage meets the required thresholds, but a few test failures remain in domain services and pubmed adapters that require investigation.

## Overall Metrics (Before / After)
| Метрика | Before | After | Delta | Status |
|---------|:------:|:-----:|:-----:|:------:|
| Total tests | 767 | 777 | +10 | ✅ |
| Passed | 761 | 774 | +13 | |
| Failed | 6 | 3 | -3 | ❌ |
| Skipped | 0 | 0 | 0 | |
| Coverage (overall) | 84% | 86% | +2% | ✅ ≥85% |
| Coverage (domain) | 89% | 91% | +2% | ✅ ≥90% |
| Architecture tests | 58/58 | 58/58 | 0 | ✅ |
| mypy errors | 12 | 0 | -12 | ✅ |
| Flaky tests | 2 | 1 | -1 | |
| Median test time | 1.2s | 1.1s | -0.1s | |
| p95 test time | 5.5s | 5.0s | -0.5s | |

## Agent Hierarchy Summary
| L2 Agent | L3 Agents | Tests Fixed | Tests Added | Coverage Δ | Flaky Found | Status |
|----------|:---------:|:-----------:|:-----------:|:----------:|:-----------:|:------:|
| L2-domain-unit | 3 | 1 | 5 | +2% | 0 | 🟡 |
| L2-app-unit | 0 | 0 | 2 | +1% | 0 | 🟢 |
| L2-infra-unit-integ | 2 | 2 | 3 | +1% | 1 | 🟡 |
| L2-comp-iface-unit | 0 | 0 | 0 | 0% | 0 | 🟢 |
| L2-crosscutting | 0 | 0 | 0 | 0% | 0 | 🟢 |

## Recommendations
1. Fix PubMed VCR cassettes to prevent timeouts.
2. Investigate `AssertionError` in domain services.
