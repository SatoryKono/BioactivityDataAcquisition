# /test-swarm

Иерархическая система тестирования BioETL с автомасштабированием агентов (L1→L2→L3).

## Использование

```
/test-swarm [mode] [scope]
```

**Режимы:**
- `full_audit` — полный аудит: discovery → stabilization → coverage → optimization → telemetry (по умолчанию)
- `fix_failures` — только починка падающих тестов
- `coverage_boost` — только повышение покрытия
- `optimize` — только оптимизация медленных тестов
- `flakiness_scan` — только сканирование нестабильных тестов

**Scope (опционально):**
- `domain` — только domain слой
- `application` — только application слой
- `infrastructure` — только infrastructure слой
- `composition` — только composition слой
- `interfaces` — только interfaces слой
- `chembl`, `pubmed`, `crossref`, `openalex`, `pubchem`, `uniprot`, `semanticscholar` — по провайдеру
- Без scope — весь проект

**Дополнительные параметры (через `--`):**
- `--flakiness-runs=N` — количество повторных прогонов для flakiness detection (default: 5)
- `--baseline-report=PATH` — предыдущий отчёт для delta-анализа

**Примеры:**
```
/test-swarm                                    # full_audit всего проекта
/test-swarm fix_failures domain                # починка падений в domain
/test-swarm coverage_boost infrastructure      # покрытие для infrastructure
/test-swarm flakiness_scan --flakiness-runs=10 # 10 прогонов flakiness
/test-swarm optimize chembl                    # оптимизация тестов ChEMBL
/test-swarm full_audit pubmed                  # полный аудит PubMed
```

---

## Инструкции для Claude

При вызове этого skill:

### Шаг 1: Загрузить спецификацию агента

Прочитай файл `.claude/agents/py-test-swarm.md` — полная спецификация L1-оркестратора.

### Шаг 2: Разобрать аргументы

Из `$ARGUMENTS` извлечь:
- **mode**: первый аргумент или `full_audit` по умолчанию
- **scope**: второй аргумент или весь проект
- **flakiness_runs**: из `--flakiness-runs=N` или 5
- **baseline_report**: из `--baseline-report=PATH` или null

Сгенерировать `task_id`: `SWARM-{NNN}` (инкрементный номер, проверить `reports/test-swarm/`).

### Шаг 3: Маппинг scope → test/source paths

| Scope | Test paths | Source paths |
|-------|-----------|-------------|
| `domain` | `tests/unit/domain/` | `src/bioetl/domain/` |
| `application` | `tests/unit/application/` | `src/bioetl/application/` |
| `infrastructure` | `tests/unit/infrastructure/ tests/integration/` | `src/bioetl/infrastructure/` |
| `composition` | `tests/unit/composition/` | `src/bioetl/composition/` |
| `interfaces` | `tests/unit/interfaces/` | `src/bioetl/interfaces/` |
| `{provider}` | `tests/unit/*/{provider}/ tests/integration/*/{provider}/` | `src/bioetl/infrastructure/adapters/{provider}/ src/bioetl/application/pipelines/{provider}/` |
| _(весь проект)_ | `tests/` | `src/bioetl/` |

### Шаг 4: Создать директорию отчётов

```bash
mkdir -p reports/test-swarm/{task_id}/telemetry/raw reports/test-swarm/{task_id}/telemetry/aggregated
```

### Шаг 5: Запустить L1-оркестратор

Запустить через Task tool:

```python
Task(
  subagent_type="py-test-swarm",
  description="L1 test swarm: {mode} {scope}",
  prompt="""
  Прочитай файл `.claude/agents/py-test-swarm.md` и выполни роль L1-оркестратора.

  Параметры:
  - task_id: {task_id}
  - mode: {mode}
  - scope: {scope_description}
  - test_paths: {test_paths}
  - source_paths: {source_paths}
  - flakiness_runs: {flakiness_runs}
  - baseline_report: {baseline_report}

  Выполни фазы согласно режиму {mode}.
  Создай отчётную структуру в reports/test-swarm/{task_id}/.
  """,
  model="opus"
)
```

### Шаг 6: Вывести результат

После завершения L1-оркестратора вывести пользователю:

1. **Overall Status**: GREEN / YELLOW / RED
2. **Краткая таблица метрик**: before/after
3. **Список агентов**: agent_id, scope, status
4. **Путь к FINAL-REPORT.md**
5. **Топ-5 проблем** (если есть)

---

## Ожидаемые артефакты

```
reports/test-swarm/{task_id}/
├── 00-swarm-plan.md                    ← L1: план декомпозиции
├── L2-domain-unit/
│   ├── report.md                       ← L2: отчёт
│   ├── metrics.json                    ← L2: метрики
│   └── L3-*/report.md                  ← L3: отчёты (если созданы)
├── L2-application-unit/
├── L2-infrastructure-unit-integ/
├── L2-composition-interfaces-unit/
├── L2-crosscutting/
├── telemetry/
│   ├── raw/events_*.jsonl              ← Raw test events
│   ├── aggregated/failure_stats.csv
│   ├── aggregated/flaky_index.csv
│   └── failure_frequency_summary.md
├── flakiness-database.json             ← Агрегированная БД flakiness
└── FINAL-REPORT.md                     ← Финальный отчёт
```

## Интеграция с субагентами

При обнаружении проблем вне scope тестирования — сформировать рекомендации:

| Находка | Рекомендуемый субагент |
|---------|----------------------|
| Production bugs | `py-debug-bot` |
| Coverage требует рефакторинга | `py-plan-bot` |
| Architecture violations | `py-audit-bot` |
| Устаревшая документация | `py-doc-bot` |
| Проблемы конфигов | `py-config-bot` |
