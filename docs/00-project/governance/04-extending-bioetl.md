# Расширение BioETL: Добавление новых Pipeline

*Синхронизировано с RULES.md v5.21 | Последнее обновление: 2026-02-21*

----------------------------------------------------------------------

## Обзор

Данный документ описывает процесс добавления новых pipeline в BioETL,
включая создание конфигураций, трансформеров и тестов.

----------------------------------------------------------------------

## 1. Чек-лист создания нового Pipeline

- [ ] Создать entity config в `configs/pipelines/<provider>/<entity>.yaml`
- [ ] Валидировать через `-schema.json`
- [ ] Выбрать каноническое имя согласно [02-naming-policy.md](02-naming-policy.md)
- [ ] Создать трансформер в `src/bioetl/application/pipelines/`
- [ ] Зарегистрировать в `PipelineRegistry`
- [ ] Добавить фабрику (при необходимости)
- [ ] Написать unit и integration тесты
- [ ] Обновить документацию провайдера

----------------------------------------------------------------------

## 2. Шаблон Entity Config

### 2.1. Минимальный шаблон

```yaml
# configs/pipelines/<provider>/<entity>.yaml
# Pipeline configuration for <Provider> <Entity>.
#
# Inherits defaults from ../-defaults.yaml:
# - dq-overrides, circuit-breaker, sink structure, maintenance, input-filter
#
# IMPORTANT: Use Canonical Terms from 02-naming-policy.md
```

### 2.2. Обязательные поля

| Поле                    | Тип    | Описание                                                                       | Требование |
| ----------------------- | ------ | ------------------------------------------------------------------------------ | ---------- |
| `pipeline-name`         | string | Формат `{provider}-{entity}`                                                   | MUST       |
| `provider`              | enum   | Один из: chembl, pubchem, uniprot, pubmed, crossref, openalex, semanticscholar | MUST       |
| `entity-type`           | string | Тип сущности                                                                   | MUST       |
| `version`               | string | Семантическая версия `X.Y.Z`                                                   | MUST       |
| `business-primary-keys` | array  | Первичный ключ                                                                 | MUST       |
| `silver-table`          | string | Имя Silver таблицы                                                             | MUST       |
| `gold-table`            | string | Имя Gold таблицы                                                               | MUST       |
| `sink`                  | object | Конфигурация слоёв                                                             | MUST       |
| `sink.*.sort-by`        | object | Сортировка для детерминизма                                                    | MUST       |

### 2.3. sort-by — Обязательное требование (ADR-014)

**MUST**: Каждый entity config должен содержать `sort-by` для Silver и Gold слоёв.

```yaml
sink:
  silver:
    sort-by:
      columns: ["primary-key-column"]  # Список колонок для сортировки
      ascending: true                   # true = ASC, false = DESC
  gold:
    sort-by:
      columns: ["primary-key-column"]
      ascending: true
```

**Почему это важно:**

- Гарантирует детерминизм выходных файлов
- Обеспечивает воспроизводимость результатов
- Стабилизирует diff-сравнения между запусками

----------------------------------------------------------------------

## 3. Валидация через JSON Schema

### 3.1. Автоматическая валидация

Все entity configs валидируются через `configs/pipelines/-schema.json`.

**Pre-commit hook:**

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: validate-pipeline-configs
      name: Validate pipeline configs
      entry: python scripts/validate-pipeline-configs.py
      language: python
      files: ^configs/pipelines/.+\.yaml$
      exclude: ^configs/pipelines/-
```

### 3.2. Ручная валидация

```bash
# Валидация одного файла
python scripts/validate-pipeline-configs.py configs/pipelines/chembl/activity.yaml

# Валидация всех конфигов
python scripts/validate-pipeline-configs.py

# Или через make
make validate-configs
```

### 3.3. Структура JSON Schema

Схема `-schema.json` проверяет:

| Проверка          | Описание                                    |
| ----------------- | ------------------------------------------- |
| `required`        | Наличие обязательных полей                  |
| `pattern`         | Формат `pipeline-name` (`^[a-z]+-[a-z-]+$`) |
| `enum`            | Допустимые значения `provider`              |
| `type`            | Типы данных полей                           |
| `minimum/maximum` | Ограничения числовых значений               |

----------------------------------------------------------------------

## 4. Создание трансформера

### 4.1. Шаблон трансформера

```python
# src/bioetl/application/pipelines/<provider>-<entity>.py
"""Трансформер для <Provider> <Entity>."""

from dataclasses import dataclass
from typing import Any

from bioetl.application.core.base-transformer import BaseTransformer


@dataclass
class <Provider><Entity>Transformer(BaseTransformer):
    """Трансформер для обработки <entity> записей из <Provider>."""

    def transform-record(self, record: dict[str, Any]) -> dict[str, Any]:
        """Трансформация одной записи.

        Args:
            record: Сырая запись из Bronze.

        Returns:
            Трансформированная запись для Silver.
        """
        return {
            "<entity>-id": record.get("<entity>-id"),
            # ... другие поля
        }

    def validate-record(self, record: dict[str, Any]) -> bool:
        """Валидация записи перед трансформацией.

        Args:
            record: Запись для валидации.

        Returns:
            True если запись валидна.
        """
        return "<entity>-id" in record
```

### 4.2. Регистрация в Registry

```python
# src/bioetl/composition/registry.py
from bioetl.application.pipelines.<provider>-<entity> import <Provider><Entity>Transformer

@register("<provider>-<entity>")
class <Provider><Entity>Pipeline:
    transformer-class = <Provider><Entity>Transformer
```

----------------------------------------------------------------------

## 5. Тестирование

### 5.1. Unit тесты трансформера

```python
# tests/unit/application/pipelines/test-<provider>-<entity>.py
import pytest
from bioetl.application.pipelines.<provider>-<entity> import <Provider><Entity>Transformer


class Test<Provider><Entity>Transformer:
    def test-transform-record-valid(self):
        transformer = <Provider><Entity>Transformer()
        record = {"<entity>-id": "123", ...}
        result = transformer.transform-record(record)
        assert result["<entity>-id"] == "123"

    def test-validate-record-missing-id(self):
        transformer = <Provider><Entity>Transformer()
        record = {}
        assert not transformer.validate-record(record)
```

### 5.2. Integration тесты с VCR

```python
# tests/integration/adapters/test-<provider>-<entity>.py
import pytest

@pytest.mark.vcr()
async def test-fetch-<entity>-from-<provider>():
    # VCR-кассета автоматически записывает HTTP-ответы
    ...
```

### 5.3. Валидация конфига

```python
# tests/unit/configs/test-<provider>-<entity>-config.py
import json
import yaml
import jsonschema


def test-<provider>-<entity>-config-valid():
    with open("configs/pipelines/-schema.json") as f:
        schema = json.load(f)
    with open("configs/pipelines/<provider>/<entity>.yaml") as f:
        config = yaml.safe-load(f)

    # Должен пройти без исключений
    jsonschema.validate(config, schema)


def test-<provider>-<entity>-has-sort-by():
    with open("configs/pipelines/<provider>/<entity>.yaml") as f:
        config = yaml.safe-load(f)

    assert "sort-by" in config["sink"]["silver"]
    assert "sort-by" in config["sink"]["gold"]
```

----------------------------------------------------------------------

## 6. Документация провайдера

После создания pipeline обновите документацию:

1. **`docs/providers/<provider>/README.md`** — добавить entity в список
1. **`docs/00-map.md`** — обновить счётчик pipelines
1. **`CLAUDE.md`** — обновить метрики (если существенные изменения)

----------------------------------------------------------------------

## 7. Пример: Добавление chembl-target-component

### 7.1. Config

```yaml
# configs/pipelines/chembl/target-component.yaml
pipeline-name: chembl-target-component
provider: chembl
entity-type: target-component
version: "1.0.0"
description: "Extract target component records from ChEMBL API"

business-primary-keys: ["component-id"]
silver-table: "chembl-target-component"
gold-table: "chembl-target-component"

source-file: ../../sources/chembl.yaml

gold-filters:
  required-fields:
    - component-id
    - component-type

sink:
  bronze:
    path: "data/output/bronze/chembl/target-component"
  silver:
    path: "data/output/silver/chembl/target-component"
    primary-key: ["component-id"]
    partition-by: []
    sort-by:
      columns: ["component-id"]
      ascending: true
    csv-export:
      path: "data/output/csv/silver/chembl/target-component"
  gold:
    path: "data/output/gold/chembl/target-component"
    sort-by:
      columns: ["component-id"]
      ascending: true
    csv-export:
      path: "data/output/csv/gold/chembl/target-component"

input-filter:
  enabled: false
```

### 7.2. Валидация

```bash
# Проверить соответствие схеме
python scripts/validate-pipeline-configs.py configs/pipelines/chembl/target-component.yaml
```

----------------------------------------------------------------------

## Связанные документы

- [03-file-policy.md](03-file-policy.md) — Политика файлов
- [ADR-014: Deterministic Writes](../../02-architecture/decisions/ADR-014-deterministic-writes.md)
- [ADR-025: Pipeline Config Unification](../../02-architecture/decisions/ADR-025-pipeline-config-unification.md)
- [03-guides/add-new-source.md](../../03-guides/add-new-source.md) — Добавление нового провайдера

----------------------------------------------------------------------

*Последнее обновление: 2026-01-14*
