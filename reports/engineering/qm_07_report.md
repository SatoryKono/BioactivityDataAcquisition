# QM-07 Verifications Report
**Revision (SHA):** $(git rev-parse HEAD)
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
**Exit Code:** 1
**Output:** No matches found. Blockers have been resolved in the codebase.

### Root/Path seams in 5 modules
**Command:** `uv run pytest tests/architecture/qm_07/test_qm07_seams.py`
**Exit Code:** 0
**Output:**
```
.                                                                        [100%]
```

### Script consumers
**Command:** `uv run pytest tests/architecture/qm_07/test_qm07_script_consumers.py`
**Exit Code:** 0
**Output:**
```
.                                                                        [100%]
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
**Output:** Successfully built bioetl-6.1.0.tar.gz and bioetl-6.1.0-py3-none-any.whl

## 3. Установленный runtime wheel
**Command:** `uv run pytest tests/architecture/qm_07/test_qm07_wheel_runtime_smoke.py`
**Exit Code:** 0
**Output:**
```
.                                                                        [100%]
```

## Итоги
- Количественные итоги: 30 cold imports проверены (MEASURED). 5 seams успешно вызваны.
- Заблокировавшая ранее core->scripts зависимость устранена (успешный тест на wheel isolation).
