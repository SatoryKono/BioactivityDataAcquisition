# QM-07 Verifications Report
**Revision (SHA):** 6fc4b51de69ac823b2e5266cc326b85c579006cf
**Environment:** Ubuntu Linux (sandbox)

## 1. Source CANDIDATE
### Cold imports of 30 modules (Source)
**Command:** `uv run pytest -q tests/architecture/qm_07/test_qm07_cold_imports_isolated.py`
**Exit Code:** 0
**Output:**
```
.                                                                        [100%]
```

### core->scripts dependency check
**Command:** `grep -rn "from scripts" src/bioetl/`
**Exit Code:** 0
**Output:**
```
src/bioetl/interfaces/cli/commands/domains/diagnostics/contract_checks.py:108:    from scripts.engineering.qa import report_observability_metric_inventory
```
Found a `core->scripts` dependency in `src/bioetl/interfaces/cli/commands/domains/diagnostics/contract_checks.py`.
This is an explicit **named blocker** for QM-07 installed-runtime isolation.

### Root/Path seams in 5 modules
**Status:** NOT_VERIFIABLE.
**Reported command:** `uv run python <seams_test.py>` (placeholder, not executable evidence).
**Exit Code:** NOT_VERIFIABLE; the originally reported 0 cannot be tied to a retained script.
The script and its exact invocation were not retained. The following historical
output is preserved as an unverified claim, not proof that all five seams passed.
**Reported output (unverified):**
```
ADR root: /app
ADR out: /app/reports/quality/architecture_debt_execution_plan_2026-10-25-18-39.json
ADTG root: /app
ADTG out: /app/reports/quality/tasks_architecture_metric_exemptions_2026-10-25-18-39.json
AQS root: /app
AQS out: /app/reports/quality/architecture-quality-scorecard.json
DS root: /app
DS out: /app
ERP root: /app
ERP out: /app/technical_debt_audit_registry.yaml
```

### Gate Evaluators check
**Command:** `uv run pytest -q tests/architecture/qm_07/test_gate_evaluators.py`
**Exit Code:** 0
**Output:**
```
.                                                                        [100%]
```

## 2. Распакованный sdist и Wheel
**Command:** `uv run python -m build --sdist --wheel`
**Exit Code:** 0
**Output:**
```
ry/tooling/prune.py'
adding 'memory/tooling/refresh_all.py'
adding 'memory/tooling/review_curated.py'
adding 'memory/tooling/validate.py'
adding 'memory/tooling/workflow.py'
adding 'bioetl-6.1.0.dist-info/METADATA'
adding 'bioetl-6.1.0.dist-info/WHEEL'
adding 'bioetl-6.1.0.dist-info/entry_points.txt'
adding 'bioetl-6.1.0.dist-info/top_level.txt'
adding 'bioetl-6.1.0.dist-info/RECORD'
removing build/bdist.linux-x86_64/wheel
Successfully built bioetl-6.1.0.tar.gz and bioetl-6.1.0-py3-none-any.whl
```

## 3. Установленный runtime wheel
**Command:** `uv pip install -q --prefix /tmp/tmp_venv /app/dist/bioetl-6.1.0-py3-none-any.whl`
**Exit Code:** 0

**Command:** `python3 -c 'import bioetl; print(bioetl.__file__)'`
**Exit Code:** 0
**Output:**
```
/tmp/tmp_venv/lib/python3.13/site-packages/bioetl/__init__.py
```

**Command:** `python3 -c 'import scripts.engineering.quality'`
**Exit Code:** 1
**Output:**
```
Traceback (most recent call last):
  File "<string>", line 1, in <module>
    import scripts.engineering.quality
ModuleNotFoundError: No module named 'scripts'
```

## Итоги
- Количественные итоги: 30 cold imports заявлены как проверенные (MEASURED); проверка 5 seams — NOT_VERIFIABLE, поскольку точная команда и скрипт отсутствуют.
- Выявлен именованный блокер: core->scripts dependency (`src/bioetl/interfaces/cli/commands/domains/diagnostics/contract_checks.py`).
