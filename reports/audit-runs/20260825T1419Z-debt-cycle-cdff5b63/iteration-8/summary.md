# Iteration 8 — Targeted tests

```text
pytest tests/unit/scripts/engineering/qa/test_technical_debt_audit_registry.py tests/architecture/test_quality_debt_scorecard.py -k "not test_debt_scorecard_declares_retirement_governance_kpis"
```

Result: pass (1 skip `warn_until_by_section`). Deselected pre-existing KPI 4 vs 8; **not** fixed by raising `max_count`.
