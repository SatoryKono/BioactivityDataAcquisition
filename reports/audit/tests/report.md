# Аудит тестовой системы

surface_score: **2** (приемлемо: ядро блокирует merge, локальные щели в наблюдаемости).
Режим: `full` / `propose-patches`. Патч не применён.
Срез: 2026-09-24T17:04:19Z. Checkout грязный (незавершённый merge), это не clean-checkout и не coverage-verify truth.

## Что реально блокирует

Единственный required context — job `pr-gate-complete` (`.github/workflows/pr-required.yml`).
Гейт `tests` в `configs/quality/github_required_checks.yaml` всегда required и включает `smoke-check`, `governance-preflight`, `test-fast`, `test-matrix`, `coverage-verify`.
`tests-complete` падает, если любой нужный lane не `success`, включая `performance-budgets` и `coverage-inventory-currentness`.

Порог покрытия задан проектом и не выдуман здесь: line и branch **85%**.
`pyproject.toml` намеренно не ставит `fail_under`, чтобы частичные шарды не падали. Жёсткий порог стоит в `coverage-verify` (`.github/workflows/tests.yml`, `coverage report --fail-under=85` и `check-branch-coverage --min-percent 85`).
Живой пересчёт coverage в этом аудите не запускался.

## Уровни

| Уровень | Где | Python-файлы |
| --- | --- | ---: |
| unit | `tests/unit/` | 2179 |
| architecture | `tests/architecture/` | 538 |
| integration | `tests/integration/` | 260 |
| contract | `tests/contract/` | 54 |
| e2e | `tests/e2e/` | 30 |
| security | `tests/security/` | 14 |
| prompts | `tests/prompts/` | 10 |
| smoke | `tests/smoke/` | 8 |
| benchmarks | `tests/benchmarks/` | 7 |
| performance | `tests/performance/` | 6 |

Отдельного `tests/migration/` и `tests/api/` нет. Контракты API живут в `tests/contract/` и scheduled `contract-tests.yml` (`REQ-TEST-006`). Миграционный уровень не выделен.

24 канонических lane — в `test-matrix.csv`. Источник: `configs/quality/test_matrix.yaml`. Модель запуска: `docs/00-project/ai/agents/guides/TEST_LANE_MENTAL_MODEL.md`.

Стек: pytest (`pyproject.toml` `[tool.pytest.ini_options]`). `pytest.ini` и `tox.ini` нет. Локальный default серийный (`forbid_global_xdist_addopts`). `pytest-rerunfailures` и `pytest.mark.flaky` в `pyproject.toml` не найдены.

## Чеклист

- Канон с чистого checkout описан (venv и `scripts/engineering/dev/run_pytest.ps1` / lane-команды). Этот прогон шёл с грязного дерева.
- Сеть по умолчанию выключена: session fixture ставит `VCR_RECORD_MODE=none`; live contract пропускается без `--network` или `BIOETL_NETWORK_TESTS` (`tests/contract/conftest.py`).
- Изоляция частичная: autouse чинит `pathlib` и `os.name`, repo-backed откатывает мутацию исходника, timeout 60 с. Общего запрета сокетов (`pytest-socket`) нет.
- Skip-census: 31 запись, все `permanent_policy`, owner есть, `temporary_debt` = 0, поэтому `expires_on` не требуется. Безусловный `@pytest.mark.skip` в unit/architecture запрещён тестом. 4 Windows/WSL architecture skip инвентаризированы (`#10418`).
- `.only` как плагин не подключён. Полный обход дерева на маркеры не завершён (процесс инвентаризации остановлен), отсутствие `.only` по всему `tests/` не доказано.

## Контрольный прогон

`.\.venv-win\Scripts\python.exe -m pytest tests/unit/domain/contracts/gold/test_protein_class_parent.py -q --tb=line -p no:benchmark -p no:xdist --timeout=60`

N=2, оба раза exit 0, по 4 кейса. Вердикт: stable. Полный suite не запускался.

## Находка

`TESTS-001` (P2, PROVEN, `REQ-TEST-005`). Job `performance-budgets` входит в блокирующий `tests-complete`, но шаг Gate on degradation report успешен, если `reports/performance/hotspot-degradation.json` нет. Генерация отчёта при отсутствии JSONL только печатает skip. Наблюдения пишутся лишь когда тест дошёл до `_record_observation`.

Патч не применён (нужно подтверждение). В шаге Gate on degradation report:

```bash
if [ ! -f reports/performance/hotspot-degradation.json ]; then
  echo "::error::Hotspot degradation report is missing."
  exit 1
fi
```

Тот же fail-closed нужен в шаге генерации отчёта, если нет `hotspot-observations.jsonl`. Бюджеты не повышать.

## Остаточный риск (не дефект политики)

`e2e-matrix-health.yml` гоняет matrix smoke 3 раза и падает на ненулевом pytest, но не входит в `github_required_checks.yaml`. Это зафиксировано: satellite, не owner `pr-gate-complete`.
16 pipeline исключены из PR smoke списком `MATRIX_REPLAY_DEFERRED_PIPELINES` (owner, `#9729`), не через голый skip.
Коммитнутый inventory `2026-09-18`: 2471/2479 fully covered, 7 partial, 0 uncovered. К текущему грязному дереву не привязан.

## Пропущено

- Полный pytest и `collect-only` всего `tests/`.
- Повтор CI flaky-telemetry (seeds 17/73/113) локально: N=0, flaky не назначался.
- Пересчёт `--cov-fail-under=85`.
- Memory pre-task/post-task.
