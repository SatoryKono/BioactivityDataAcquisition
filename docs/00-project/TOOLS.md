# BioETL: Утилиты Проекта

*Версия: 2.1 | Синхронизировано с RULES.md v5.20 (2026-02-17)*

---

## Разграничение src/tools/ и scripts/

Согласно **03-file-policy.md**, проект разделяет вспомогательные скрипты:

| Директория | Назначение | Критерий |
|------------|------------|----------|
| `src/tools/` | Утилиты проекта | **Импортирует** `bioetl` модули |
| `scripts/` | CI/операционные скрипты | **Standalone**, НЕ импортирует `bioetl` |

**Правило**: Если скрипт использует `from bioetl...` или `import bioetl...` → `src/tools/`, иначе → `scripts/`.

---

## Содержание

1. [src/tools/ — Утилиты с зависимостями bioetl](#srctools--утилиты-с-зависимостями-bioetl)
2. [scripts/ — Standalone скрипты](#scripts--standalone-скрипты)
3. [Бенчмарки](#бенчмарки)
4. [Интеграция с Make](#интеграция-с-make)
5. [Добавление нового инструмента](#добавление-нового-инструмента)

---

## src/tools/ — Утилиты с зависимостями bioetl

Эти инструменты **импортируют** модули `bioetl` и требуют установленного пакета.

### create-pipeline.py

**Назначение:** Генерация boilerplate-кода для новых BioETL пайплайнов.

**Зависимости bioetl:**
- `bioetl.application.core.base.BasePipeline`
- `bioetl.application.core.base-transformer.BaseTransformer`
- `bioetl.composition.registry.register-pipeline`
- `bioetl.domain.context.PipelineContext`

**Создаёт:**
```
src/bioetl/application/pipelines/{provider}/{entity}/
├── --init--.py
├── pipeline.py      # {Provider}{Entity}Pipeline
├── transformer.py   # {Provider}{Entity}Transformer
└── config.py        # Config model

configs/pipelines/{provider}/{entity}.yaml
tests/unit/application/pipelines/{provider}/test-{entity}.py
```

**Использование:**
```bash
# Создать новый пайплайн
python src/tools/create-pipeline.py --provider chembl --entity document

# Dry-run (preview без создания файлов)
python src/tools/create-pipeline.py --provider pubchem --entity compound --dry-run
```

| Параметр | Описание |
|----------|----------|
| `--provider` | Имя провайдера (chembl, pubchem, etc.) |
| `--entity` | Имя сущности (activity, molecule, etc.) |
| `--dry-run` | Только показать генерируемые файлы |

**Ссылки:** 03-file-policy.md §Пайплайны

---

### verify-schema-parity.py

**Назначение:** Программная верификация соответствия схем между Domain entities и Infrastructure schemas.

**Зависимости bioetl:**
- `bioetl.domain.entities.bioactivity.Bioactivity`
- `bioetl.domain.entities.chembl-activity.Assay`
- `bioetl.domain.entities.chembl-structures.Molecule, Target`
- `bioetl.infrastructure.schemas.gold`
- `bioetl.infrastructure.schemas.silver`

**Использование:**
```bash
python src/tools/verify-schema-parity.py
```

**Проверяет паритет:**
- `Bioactivity` ↔ `ChEMBLActivityGoldSchema`
- `Molecule` ↔ `ChEMBLMoleculeGoldSchema`
- `Target` ↔ `ChEMBLTargetGoldSchema`
- `Assay` ↔ `ChEMBLAssayGoldSchema`

---

### file-merger.py

**Назначение:** Объединение нескольких файлов проекта в один выходной файл с метаданными.

**Использование:**
```bash
# Объединить файлы из директории
python src/tools/file-merger.py --dir src/bioetl/domain/ --ext .py --output merged.txt
```

| Параметр | Описание |
|----------|----------|
| `--dir` | Директория для рекурсивного обхода |
| `--ext` | Фильтр расширений файлов |
| `--output` | Путь к выходному файлу |

---

## scripts/ — Standalone скрипты

Эти скрипты **НЕ импортируют** `bioetl` и используют только stdlib/внешние библиотеки.

### cleanup-project.py

**Назначение:** Очистка кэшей, build-артефактов и временных файлов.

**Использование:**
```bash
# Dry-run (по умолчанию)
python scripts/cleanup-project.py

# Применить изменения с архивированием логов
python scripts/cleanup-project.py --apply --archive-logs

# Полная очистка (включая логи)
python scripts/cleanup-project.py --apply --purge-logs
```

| Флаг | Описание |
|------|----------|
| `--dry-run` | Показать кандидатов на удаление (default) |
| `--apply` | Выполнить удаление |
| `--archive-logs` | Переместить логи в `reports/` |
| `--purge-logs` | Принудительно удалить логи |

**Ссылки:** 05-cleanup-policy.md §4.2

**Make-цель:** `make clean-dev`

---

### cleanup-consolidate.py

**Назначение:** Консолидированный аудит очистки и качества проекта (dry-run по умолчанию).

**Использование:**
```bash
# Dry-run (по умолчанию)
python scripts/cleanup-consolidate.py

# Применить удаление .pyc/--pycache--/temp файлов
python scripts/cleanup-consolidate.py --apply
```

**Что анализирует:**
- `.pyc`, `--pycache--`, временные файлы (по шаблонам cleanup-project.py);
- YAML-конфиги без ссылок в коде/конфигах;
- дубликаты функций в утилитарных модулях (AST);
- неиспользуемые импорты (AST + текстовая проверка);
- неиспользуемые зависимости по `pyproject.toml` и фактическим импортам.

**Связанные инструменты:** `cleanup-project.py` — фактическая очистка кэшей и артефактов.

---

### vacuum-delta.py

**Назначение:** Еженедельный VACUUM для Delta Lake таблиц Silver слоя.

**Использование:**
```bash
# VACUUM всех Silver таблиц
python scripts/vacuum-delta.py

# VACUUM конкретной таблицы
python scripts/vacuum-delta.py --table silver/chembl/activity

# С кастомным retention
python scripts/vacuum-delta.py --retention-days 14
```

| Параметр | Описание | Default |
|----------|----------|---------|
| `--table` | Путь к конкретной таблице | Все Silver |
| `--retention-days` | Период хранения файлов | 7 |
| `--dry-run` | Только показать файлы к удалению | False |

**Ссылки:** RULES.md §2.1.1, 05-cleanup-policy.md §4.3

**Make-цель:** `make vacuum-silver`

---

### salt-rotate.py

**Назначение:** Ротация соли для хеширования PII-данных.

**Использование:**
```bash
# Стандартная ротация
python scripts/salt-rotate.py

# Экстренная ротация (инцидент безопасности)
python scripts/salt-rotate.py --emergency
```

| Параметр | Описание |
|----------|----------|
| `--emergency` | Немедленная ротация без периода перехода |
| `--verify` | Проверить текущее состояние соли |

**Ссылки:** RULES.md §5.4.1

---

### dq-baseline-update.py

**Назначение:** Пересчёт baseline для Data Quality метрик.

**Использование:**
```bash
# Пересчитать baseline для всех пайплайнов
python scripts/dq-baseline-update.py

# Для конкретного пайплайна
python scripts/dq-baseline-update.py --pipeline chembl-activity
```

| Параметр | Описание |
|----------|----------|
| `--pipeline` | Имя пайплайна (default: все) |
| `--window-days` | Окно для расчёта baseline |

**Ссылки:** RULES.md §3.4.1

---

### verify-checksums.py

**Назначение:** Верификация контрольных сумм критических артефактов после DR-восстановления.

**Использование:**
```bash
python scripts/verify-checksums.py
python scripts/verify-checksums.py --table silver/chembl/activity
```

**Ссылки:** 05-cleanup-policy.md §5.2

**Make-цель:** `make verify-checksums`

---

### audit-structure.py

**Назначение:** Проверяет соответствие структуры проекта File Policy (`03-file-policy.md`).

**Использование:**
```bash
# Стандартный аудит
python scripts/audit-structure.py

# JSON вывод для CI
python scripts/audit-structure.py --json

# Строгий режим (SHOULD violations = exit 1)
python scripts/audit-structure.py --strict
```

| Флаг | Описание |
|------|----------|
| `--json` | Вывод результатов в JSON формате |
| `--strict` | Exit code 1 при нарушениях SHOULD (default: только MUST) |

**Ссылки:** 03-file-policy.md

---

### naming-audit.py

**Назначение:** Валидация naming conventions согласно RULES.md §2.

**Проверяет:**
- Classes: PascalCase с role-appropriate суффиксами
- Modules: snake-case
- Functions: snake-case с семантическими префиксами
- Documentation: kebab-case (или NN- префикс для ordered docs)
- YAML Configs: snake-case
- Constants: UPPER-SNAKE-CASE

**Использование:**
```bash
# Полный аудит
python scripts/naming-audit.py

# CI режим (exit 1 при нарушениях)
python scripts/naming-audit.py --check

# Сохранить отчёт в файл
python scripts/naming-audit.py --output report.md
```

**Ссылки:** RULES.md §2, docs/glossary.md

---

### lint-terminology.py

**Назначение:** Линтер для проверки терминологии в коде и документации.

**Использование:**
```bash
# Проверить весь проект
python scripts/lint-terminology.py

# Проверить конкретный файл
python scripts/lint-terminology.py src/bioetl/domain/models/molecule.py

# Автоисправление (где возможно)
python scripts/lint-terminology.py --fix
```

**Что проверяет:**
- Соответствие терминов `docs/glossary.md`
- Provider-specific naming (Molecule vs Compound)
- Deprecated terms

**Ссылки:** docs/glossary.md

---

### render-diagrams.py

**Назначение:** Валидация и рендеринг Mermaid диаграмм из `docs/`.

**Использование:**
```bash
python scripts/render-diagrams.py
```

> **Примечание:** Текущая версия — placeholder для валидации существования файлов.

---

### config-gap-analysis.py

**Назначение:** Анализ расхождений между конфигурациями пайплайнов и фактическим кодом.

**Использование:**
```bash
python scripts/config-gap-analysis.py
```

**Что анализирует:**
- Пропущенные entity configs для зарегистрированных пайплайнов
- Несоответствия между конфигурацией и кодовой базой
- Отсутствующие поля в entity configs

---

### validate-pipeline-configs.py

**Назначение:** Валидация всех pipeline configs против JSON Schema.

**Использование:**
```bash
python scripts/validate-pipeline-configs.py
```

**Что проверяет:**
- Соответствие `-schema.json` для всех entity configs
- Обязательные поля (`pipeline-name`, `provider`, `entity-type`, etc.)
- Корректность `sink` путей и `sort-by` конфигурации

---

## Бенчмарки

Директория `src/tools/benchmarks/` содержит performance-тесты для критических операций.

| Файл | Назначение |
|------|------------|
| `test-bronze-write.py` | Бенчмарки записи Bronze слоя |
| `test-delta-write.py` | Бенчмарки Delta Lake операций |
| `test-json-serialization.py` | Сравнение JSON encoders (stdlib vs orjson) |

```bash
# Запуск бенчмарков
pytest src/tools/benchmarks/ -v --benchmark-only
```

---

## Интеграция с Make

```makefile
# Очистка
clean-dev:
    python scripts/cleanup-project.py --apply --purge-logs

# Delta Lake maintenance
vacuum-silver:
    python scripts/vacuum-delta.py

# Верификация
verify-checksums:
    python scripts/verify-checksums.py

# Аудит
audit-structure:
    python scripts/audit-structure.py

audit-naming:
    python scripts/naming-audit.py

# Создание пайплайна (требует bioetl)
new-pipeline:
    python src/tools/create-pipeline.py --provider $(PROVIDER) --entity $(ENTITY)
```

---

## Добавление нового инструмента

### Критерий размещения

1. Скрипт импортирует `bioetl` → **src/tools/**
2. Скрипт standalone (только stdlib/внешние) → **scripts/**

### Шаблон для src/tools/ (с bioetl)

```python
#!/usr/bin/env python3
"""
{tool-name}.py - {краткое описание}.

Использование:
    python src/tools/{tool-name}.py [--option VALUE]

Зависимости bioetl:
    - bioetl.{module}

Ссылки:
    - RULES.md §X.Y: {описание правила}
"""
from --future-- import annotations

import argparse
from pathlib import Path

from bioetl.infrastructure.logging import get-logger

logger = get-logger(--name--)
PROJECT-ROOT = Path(--file--).parent.parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(description=--doc--)
    parser.add-argument("--dry-run", action="store-true", help="Preview only")
    args = parser.parse-args()

    logger.info("Starting tool", tool=--name--, dry-run=args.dry-run)
    # ... implementation ...
    return 0


if --name-- == "--main--":
    raise SystemExit(main())
```

### Шаблон для scripts/ (standalone)

```python
#!/usr/bin/env python3
"""
{script-name}.py - {краткое описание}.

Standalone скрипт (НЕ импортирует bioetl).

Использование:
    python scripts/{script-name}.py [--option VALUE]

Ссылки:
    - RULES.md §X.Y: {описание правила}
"""
from --future-- import annotations

import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(--name--)

PROJECT-ROOT = Path(--file--).parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(description=--doc--)
    args = parser.parse-args()

    # ... implementation (без bioetl imports) ...
    return 0


if --name-- == "--main--":
    raise SystemExit(main())
```

---

## Сводная таблица

| Файл | Директория | Импортирует bioetl | Make-цель |
|------|------------|-------------------|-----------|
| `create-pipeline.py` | src/tools/ | Да | `make new-pipeline` |
| `verify-schema-parity.py` | src/tools/ | Да | — |
| `file-merger.py` | src/tools/ | Нет | — |
| `cleanup-project.py` | scripts/ | Нет | `make clean-dev` |
| `vacuum-delta.py` | scripts/ | Нет | `make vacuum-silver` |
| `salt-rotate.py` | scripts/ | Нет | — |
| `dq-baseline-update.py` | scripts/ | Нет | — |
| `verify-checksums.py` | scripts/ | Нет | `make verify-checksums` |
| `audit-structure.py` | scripts/ | Нет | `make audit-structure` |
| `naming-audit.py` | scripts/ | Нет | `make audit-naming` |
| `lint-terminology.py` | scripts/ | Нет | — |
| `render-diagrams.py` | scripts/ | Нет | — |
| `config-gap-analysis.py` | scripts/ | Нет | — |
| `validate-pipeline-configs.py` | scripts/ | Нет | — |

---

## Связи с документацией

| Документ | Связанные инструменты |
|----------|----------------------|
| 03-file-policy.md | `audit-structure.py`, `create-pipeline.py` |
| 05-cleanup-policy.md | `cleanup-project.py`, `vacuum-delta.py`, `verify-checksums.py` |
| RULES.md §2 | `naming-audit.py` |
| RULES.md §2.1.1 | `vacuum-delta.py` |
| RULES.md §3.4.1 | `dq-baseline-update.py` |
| RULES.md §5.4.1 | `salt-rotate.py` |
| docs/glossary.md | `lint-terminology.py` |
| 03-file-policy.md (configs) | `config-gap-analysis.py`, `validate-pipeline-configs.py` |

---

## История изменений

| Версия | Дата | Изменения |
|--------|------|-----------|
| 2.0 | 2026-01-07 | Разделение на src/tools/ и scripts/ по критерию импорта bioetl |
| 1.1 | 2026-01-07 | Добавлены все инструменты |
| 1.0 | 2025-01-07 | Начальная версия |
