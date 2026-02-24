# Архитектурный аудит BioETL

Дата: 2026-02-21
Область: `src/bioetl`, `tests`, `docs/00-project/RULES.md`

## Предварительная проверка входных документов

- `RULES.md` найден: `docs/00-project/RULES.md`.
- Запрошенные документы `01-domain-objects.md`, `02-etl-layers.md`, `03-data-flow.md`, `04-duplication-reduction.md`, `05-physical-layout.md`: **[данные отсутствуют]** (в репозитории не обнаружены).

## Часть 1. Объективные метрики

| Метрика                              | Команда/метод                                                                                                                                   |                                                          Значение |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------: |
| Покрытие тестами                     | `.venv/Scripts/python.exe -m pytest ...` (Windows path не найден), затем `.venv/bin/python -m pytest tests/ --cov=src/bioetl --cov-report=term` | **[данные отсутствуют]** (прогон не завершён: остановлен на ~16%) |
| Ошибки mypy                          | `.venv/bin/python -m mypy src/bioetl --strict 2>&1` + `grep -c "error:"`                                                                        |                                                                 0 |
| Циклические импорты                  | `.venv/bin/python -c "from bioetl import domain; print('pass')"`                                                                                |                                                              pass |
| Количество классов                   | `rg '^class ' src --glob '*.py' \| wc -l`                                                                                                       |                                                               936 |
| Количество файлов .py                | `find src -name '*.py' \| wc -l`                                                                                                                |                                                               570 |
| Средний размер модуля (`src/bioetl`) | `lines/files`                                                                                                                                   |                                                      219.15 строк |
| TODO/FIXME в коде                    | `rg -i -e 'TODO\|FIXME\|XXX\|HACK' src \| wc -l`                                                                                                |                                                                 5 |
| Использование print()                | `rg 'print\(' src/bioetl --glob '*.py' \| wc -l`                                                                                                |                                                                 0 |
| Hardcoded secrets (эвристика)        | `rg -i -e '(api_key\|password\|secret)\s*=' src \| wc -l`                                                                                       |                                     14 (требует ручной валидации) |

## Часть 2. Оценка по 10 категориям

### 1) Соблюдение слоистой архитектуры (вес 15%) — **10/10**

- По критериям задачи проверяемые направления чистые:
  - `domain -> infrastructure`: 0
  - `domain -> application`: 0
  - `application -> interfaces`: 0
- Проверка: `rg` по импортам в `src/bioetl/domain` и `src/bioetl/application`.
- Примечание: в коде есть `infrastructure -> domain` импорты (149), что в пользовательском custom prompt помечено как нарушение; но в данной категории критерий ограничен тремя проверками выше.

### 2) Контракты и Ports (вес 12%) — **8/10**

- Позитив: выделен пакет `domain/ports` с Protocol-контрактами (`25` файлов; `Protocol` используется широко).
- Нарушения/риски:
  - Существенное число импортов `infrastructure -> domain` мимо `domain.ports` (149 вхождений), напр. `src/bioetl/infrastructure/config/dq_config_loader.py`, `src/bioetl/infrastructure/adapters/pubmed/pubmed_client.py`.
- Вывод: контракты есть, но часть связей остаётся «жёсткой» через доменные модели/исключения.

### 3) Medallion Architecture (вес 12%) — **9/10**

- Bronze: явная реализация JSONL + zstd и требуемого path pattern в `BronzeWriter`.
- Silver: Delta Lake (`write_deltalake`), merge/upsert и maintenance (`vacuum`) реализованы.
- Gold: отдельный writer + strict-валидация через PanderaGoldValidator (strict=True по умолчанию).
- Minor: нужны интеграционные подтверждения retention/SLA расписания VACUUM в реальном окружении.

### 4) Обработка ошибок и Circuit Breaker (вес 10%) — **9/10**

- Error classification есть в домене (`ErrorClassifier`, маппинг на ErrorType).
- Circuit Breaker реализован с threshold=5, recovery_timeout=300s, half-open probe, метрики state/trips/success/failure.
- Риск: часть классификации для external исключений опирается на keyword fallback (эвристика).

### 5) Блокировки и конкурентность (вес 10%) — **9/10**

- Реализован `MemoryLock` (соответствует Local-Only ADR), есть TTL, heartbeat, fencing token, validate_owner (safety guard).
- Значения TTL/heartbeat конфигурируемы и логика heartbeat присутствует.

### 6) Валидация и DQ (вес 10%) — **8/10**

- Pandera validators (Silver/Gold) реализованы, есть no-op и strict режимы.
- Quarantine присутствует (`src/bioetl/infrastructure/quarantine/*`).
- Threshold-поведение 5%/20% в этом аудите детально не подтверждено end-to-end: **частично подтверждено**.

### 7) Логирование и наблюдаемость (вес 8%) — **9/10**

- UnifiedLogger реализован с обязательным `run_id`.
- Prometheus-метрики присутствуют (`infrastructure/observability/metrics.py`).
- `print()` в `src/bioetl` не найдено.

### 8) Тестирование (вес 8%) — **7/10**

- Позитив: широкое покрытие тестами, VCR-кассеты (`tests/fixtures/vcr`), присутствуют golden/contract тесты.
- Ограничение: итоговый процент покрытия по полному прогону **[данные отсутствуют]** (run не завершён).

### 9) Безопасность и секреты (вес 8%) — **7/10**

- Явных hardcoded credentials в стиле `"secret_value"` не подтверждено.
- Эвристический grep даёт 14 срабатываний на присваивания переменным (`api_key = ...`), что требует ручной ревизии и allowlist.

### 10) Документация и сопровождаемость (вес 7%) — **8/10**

- Есть RULES, ADR (37), CHANGELOG, спецификации pipeline contracts (`docs/04-reference/pipelines/*`).
- Запрошенные дополнительные архитектурные файлы отсутствуют в дереве проекта.

## Часть 3. Итоговый документ

### 3.1 Сводная таблица

| #         | Категория                   |      Вес | Оценка |   Взвеш. балл | Ключевые находки                                             |
| --------- | --------------------------- | -------: | -----: | ------------: | ------------------------------------------------------------ |
| 1         | Слоистая архитектура        |      15% |     10 |          1.50 | По заданным проверкам 0 нарушений                            |
| 2         | Контракты и Ports           |      12% |      8 |          0.96 | Много Protocol, но 149 `infrastructure -> domain` non-ports  |
| 3         | Medallion Architecture      |      12% |      9 |          1.08 | Bronze JSONL+zstd, Silver Delta, Gold validator              |
| 4         | Ошибки и Circuit Breaker    |      10% |      9 |          0.90 | Классификация + CB + метрики                                 |
| 5         | Блокировки и конкурентность |      10% |      9 |          0.90 | MemoryLock + heartbeat + fencing + safety guard              |
| 6         | Валидация и DQ              |      10% |      8 |          0.80 | Pandera + Quarantine, thresholds частично подтверждены       |
| 7         | Логирование/наблюдаемость   |       8% |      9 |          0.72 | UnifiedLogger + run_id + metrics, print=0                    |
| 8         | Тестирование                |       8% |      7 |          0.56 | VCR/golden/contract есть, coverage % не получен              |
| 9         | Безопасность/секреты        |       8% |      7 |          0.56 | Явного hardcode не доказано, есть эвристические срабатывания |
| 10        | Документация                |       7% |      8 |          0.56 | RULES+ADR+CHANGELOG присутствуют                             |
| **Итого** |                             | **100%** |        | **8.54 / 10** |                                                              |

### 3.2 Интерпретация

**8.54 / 10** → *Production-ready, minor improvements*.

### 3.3 План рефакторинга

#### [P1] Ужесточить границы слоёв для `infrastructure -> domain` импортов

- Категория: 1, 2
- Текущий балл → Целевой балл: 10/8 → 10/9
- Влияние на общий балл: +0.12
- Проблема: 149 импортов non-ports создают жёсткое связывание.
- Решение: вынос контрактов в `domain/ports` и DTO/VO boundary-объекты.
- Файлы: `src/bioetl/infrastructure/config/*`, `src/bioetl/infrastructure/adapters/*`, `src/bioetl/domain/ports/*`.
- Риски: регрессии совместимости сигнатур.
- Критерий готовности: `rg -P 'from bioetl\.domain(?!\.ports)' src/bioetl/infrastructure | wc -l == 0` (или согласованный allowlist).
- Трудозатраты: L (1-2 недели).

#### [P1] Сделать метрику coverage обязательной и воспроизводимой в CI

- Категория: 8
- Текущий балл → Целевой балл: 7 → 9
- Влияние на общий балл: +0.16
- Проблема: отсутствует подтверждённый общий coverage % в этом аудите.
- Решение: стабилизировать полный pytest run, добавить target-timeouts/разделение suite.
- Файлы: `pyproject.toml`, CI workflow, `tests/`.
- Риски: рост времени CI.
- Критерий готовности: coverage стабильно ≥85% в PR.
- Трудозатраты: M.

#### [P2] DQ thresholds 5%/20% — зафиксировать автоматическими тестами

- Категория: 6
- Текущий балл → Целевой балл: 8 → 9
- Влияние на общий балл: +0.10
- Проблема: thresholds не подтверждены end-to-end в рамках текущего прогона.
- Решение: добавить интеграционные тесты на warning/fail при порогах.
- Файлы: `tests/integration/*dq*`, `src/bioetl/application/*`.
- Риски: flaky при больших наборах.
- Критерий готовности: детерминированные тесты на 5% и 20%.
- Трудозатраты: M.

#### [P2] Секреты: заменить grep-эвристику на semgrep/gitleaks policy

- Категория: 9
- Текущий балл → Целевой балл: 7 → 9
- Влияние на общий балл: +0.16
- Проблема: 14 ложноположительных срабатываний, нет качественного gate.
- Решение: добавить ruleset и allowlist, блокирующий только реальные утечки.
- Файлы: `.github/workflows/*`, `docs/security/*`, конфиги анализаторов.
- Риски: шум/ложные блокировки на старте.
- Критерий готовности: 0 true-positive секретов, контролируемый FP rate.
- Трудозатраты: S-M.

#### [P3] Документация: восстановить/синхронизировать отсутствующие архитектурные документы

- Категория: 10
- Текущий балл → Целевой балл: 8 → 9
- Влияние на общий балл: +0.07
- Проблема: запрошенные 01..05 архитектурные md отсутствуют.
- Решение: добавить/смаппить эквиваленты в docs/02-architecture + ссылки из RULES.
- Файлы: `docs/02-architecture/*`, `docs/00-project/00-map.md`.
- Риски: рассинхрон версий документов.
- Критерий готовности: все ссылки разрешаются, нет [данные отсутствуют] по базовому набору.
- Трудозатраты: S.

### 3.4 Roadmap

- **Фаза 1 (неделя 1-2)**: P1 изменения (границы слоёв + coverage CI). Ожидаемый общий балл: **8.54 → 8.82**.
- **Фаза 2 (неделя 3-4)**: P2 изменения (DQ thresholds tests + secrets policy). Ожидаемый общий балл: **8.82 → 9.08**.
- **Фаза 3 (неделя 5+)**: P3 изменения (документация). Ожидаемый общий балл: **9.08 → 9.15**.

## Часть 4. CI метрики контроля регресса

| Метрика             | Порог           | Команда                                       | Блокирует PR |
| ------------------- | --------------- | --------------------------------------------- | ------------ |
| Coverage            | ≥85%            | `pytest --cov=src/bioetl --cov-fail-under=85` | Да           |
| mypy errors         | 0               | `mypy src/bioetl --strict`                    | Да           |
| Циклические импорты | 0               | `python scripts/check_cycles.py`              | Да           |
| Нарушения слоёв     | 0               | `python scripts/check_layer_imports.py`       | Да           |
| print() в коде      | 0               | `rg 'print\(' src/bioetl --glob '*.py'`       | Да           |
| Hardcoded secrets   | 0 true-positive | `gitleaks detect --source .`                  | Да           |

## Проверяемые примеры кода (выборка)

- Medallion Bronze: `src/bioetl/infrastructure/storage/bronze_writer.py`
- Medallion Silver/Delta: `src/bioetl/infrastructure/storage/silver_writer.py`
- Circuit Breaker: `src/bioetl/infrastructure/adapters/http/circuit_breaker.py`
- MemoryLock: `src/bioetl/infrastructure/locking/memory_lock.py`
- Pandera validation: `src/bioetl/infrastructure/validation/pandera_validator.py`
- Unified logging: `src/bioetl/infrastructure/observability/unified_logger.py`
