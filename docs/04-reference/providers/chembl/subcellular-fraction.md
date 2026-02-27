# Пайплайн: ChEMBL Subcellular Fraction

**Имя пайплайна:** `chembl_subcellular_fraction`
**Провайдер:** `chembl`
**Сущность:** `subcellular_fraction`
**Версия схемы:** 1.0.0

---

## 1. Описание

Пайплайн извлекает данные о субклеточных фракциях из API ChEMBL. Субклеточные фракции описывают клеточные компартменты или препараты, используемые в биоанализах (например, "Microsomes", "Cytosol", "Mitochondria"). Это производная (derived) сущность — данные извлекаются из ответов Assay API и дедуплицируются.

**Источник данных:** ChEMBL REST API, эндпоинт `/assay` (извлечение уникальных subcellular_fraction)

---

## 2. Ключевые поля

### Идентификаторы

| Поле | Тип | Описание |
|------|-----|----------|
| `entity_id` | `str` | SHA256 хэш нормализованного названия фракции (PK) |
| `subcellular_fraction` | `str` | Название субклеточной фракции |

### Метаданные

| Поле | Тип | Описание |
|------|-----|----------|
| `content_hash` | `str` | SHA256 content hash для дедупликации |
| `ingestion_ts` | `datetime` | Время загрузки записи |

---

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/chembl/subcellular_fraction_transformer.py`

### Нормализация данных

- **subcellular_fraction:** Строка нормализуется (strip whitespace, lowercase)
- **entity_id:** Вычисляется как SHA256 хэш нормализованного имени фракции
- **Дедупликация:** На уровне `SubcellularFractionDataSource` (до трансформации)

### Entity ID

```python
entity_id = sha256(normalize(subcellular_fraction))
```

---

## 4. Валидация

### DQ-правила

1. **`subcellular_fraction`** — обязательное, непустая строка
2. **`entity_id`** — обязательное, формат SHA256

### Пороги ошибок

| Порог | Условие | Действие |
|-------|---------|----------|
| Soft | > 5% ошибок | WARNING |
| Hard | > 20% ошибок | FAIL BATCH |

---

## 5. Использование CLI

```bash
# Инкрементальная загрузка
bioetl run chembl_subcellular_fraction

# С ограничением количества записей
bioetl run chembl_subcellular_fraction --limit 500

# Полная перезагрузка
bioetl run chembl_subcellular_fraction --run-type rebuild
```

---

## 6. Связанные файлы

| Компонент | Путь |
|-----------|------|
| Конфигурация | `configs/entities/chembl/subcellular_fraction.yaml` |
| Трансформер | `src/bioetl/application/pipelines/chembl/subcellular_fraction_transformer.py` |
| Data Source | `src/bioetl/application/core/subcellular_fraction_data_source.py` |
| Pipeline Spec | `docs/04-reference/pipelines/chembl/14-subcellular-fraction-spec.md` |

---

## 7. Связи с другими сущностями

```
Subcellular Fraction (entity_id)
    └── Assay (assay_subcellular_fraction) [N:1 lookup]
        └── Activity [1:N]
```

---

*Последнее обновление: 2026-02-27*
