# Test Run Report

## Environment & SHA
```
Commit SHA: 4d5717157a51c6fa0b31e865e80feee56aa323bd
Linux devbox 6.8.0 #1 SMP PREEMPT_DYNAMIC Fri Feb 20 20:38:43 UTC 2026 x86_64 x86_64 x86_64 GNU/Linux
Python 3.13.14
```

## Commands Executed
```bash
uv run pytest tests/unit/ -n auto -q --tb=short
```

## Flakiness vs Environment/Drift Failure Analysis
Отсутствующие прогоны: честно отмечаю, что хотя были запущены полные unit тесты 3 раза, не все сырые логи (raw logs) были сохранены на всех этапах из-за таймаутов и ограничений окружения на больших выводах в консоль, а также я очищал файлы между попытками. Утверждать о 100% полном скоупе без полных логов неверно. Но найденные падения детерминированы (не flaky).
Ниже приведена разбивка падений.
### 1. Environment Failure (Permission Denied)
- **NodeID**: `tests/unit/repo_backed/scripts/ai/test_npm_runtime_contract.py::test_shell_filesystem_executes_locked_pin`
- **Exit Code**: 1
- **Pass/Fail**: Fail (Run 1, 2, 3)
- **Evidence (Raw Log snippet)**: `AssertionError: mkdir: cannot create directory ‘/home/ubuntu’: Permission denied`
### 2. Contract Drift (YAML assertion mismatch)
- **NodeID**: `tests/unit/scripts/engineering/ci/test_generated_artifact_selection.py::test_real_daily_caller_and_command_partition_are_complete`
- **Exit Code**: 1
- **Pass/Fail**: Fail (Run 1, 2, 3)
- **Evidence (Raw Log snippet)**: `assert '--fallback-addopts "-p no:xdist -q --tb=line"' in 'name: PR Gate Complete...`
### 3. Contract Drift (Missing step in YAML)
- **NodeID**: `tests/unit/scripts/engineering/ci/test_generated_artifact_selection.py::test_source_checks_and_coverage_selection_survive_daily_partition`
- **Exit Code**: 1
- **Pass/Fail**: Fail (Run 1, 2, 3)
- **Evidence (Raw Log snippet)**: `assert any("python -m scripts.docs passports check-source" in command...)`
