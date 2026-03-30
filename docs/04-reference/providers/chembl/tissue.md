---
Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-03-29'
---

# Пайплайн: ChEMBL Tissue

**Имя пайплайна:** `chembl_tissue`
**Провайдер:** `chembl`
**Сущность:** `tissue`
**Версия схемы:** 1.0.0

---

## 1. Описание

Пайплайн извлекает данные о тканях и анатомических локациях из API ChEMBL. Ткани используются как контекст для описания условий экспериментов (assays). Сущность Tissue имеет связь 1:N с Assay (через FK `assay.tissue_id`).

**Источник данных:** ChEMBL REST API, эндпоинт `/tissue`

---

## 2. Ключевые поля

### Идентификаторы

| Поле | Тип | Описание |
|------|-----|----------|
| `tissue_id` | `str` | Уникальный ChEMBL ID ткани (PK, формат `CHEMBL\d+`) |
| `pref_name` | `str` | Предпочтительное название ткани |

### Онтологические ссылки

| Поле | Тип | Описание |
|------|-----|----------|
| `bto_id` | `str` | Brenda Tissue Ontology ID (формат: `BTO:0000000`) |
| `caloha_id` | `str` | CALIPHO tissue ID (формат: `TS-0000`) |
| `efo_id` | `str` | EFO ontology ID (формат: `EFO:0000000`) |
| `uberon_id` | `str` | UBERON anatomy ontology ID (формат: `UBERON:0000000`) |

---

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/chembl/tissue_transformer.py`

### Нормализация данных

- **pref_name:** Строка нормализуется через `normalize_to_string()` (strip whitespace)
- **Онтологические ID:** Пустые строки и whitespace преобразуются в `NULL`
- **tissue_id:** Валидируется через regex `^CHEMBL\d+$`

### Entity ID

```python
entity_id = f"chembl:{tissue_id}"
```

---

## 4. Валидация

### DQ-правила

1. **`tissue_id`** — обязательное, формат `^CHEMBL\d+$`
2. **`pref_name`** — обязательное, длина 1-200 символов
3. **`bto_id`** — если указан, формат `^BTO:\d{7}$`
4. **`caloha_id`** — если указан, формат `^TS-\d{4}$`
5. **`efo_id`** — если указан, формат `^EFO:\d{7}$`
6. **`uberon_id`** — если указан, формат `^UBERON:\d{7}$`

### Пороги ошибок

| Порог | Условие | Действие |
|-------|---------|----------|
| Soft | > 5% ошибок | WARNING |
| Hard | > 20% ошибок | FAIL BATCH |

---

## 5. Использование CLI

```bash
# Инкрементальная загрузка
bioetl run --pipeline chembl_tissue

# С ограничением количества записей
bioetl run --pipeline chembl_tissue --limit 500

# Полная перезагрузка
bioetl run --pipeline chembl_tissue --run-type rebuild
```

---

## 6. Связанные файлы

| Компонент | Путь |
|-----------|------|
| Конфигурация | `configs/entities/chembl/tissue.yaml` |
| DQ Rules | `configs/entities/chembl/tissue.yaml#quality` |
| Схема | `configs/entities/chembl/tissue.yaml` |
| Трансформер | `src/bioetl/application/pipelines/chembl/tissue_transformer.py` |

---

## 7. Связи с другими сущностями

```
Tissue (tissue_id)
    └── Assay (tissue_id FK) [1:N]
        └── Activity [1:N]
```

---

## 8. Примеры данных

### Bronze (raw JSON)

```json
{
  "tissue_id": "CHEMBL3638186",
  "pref_name": "Liver",
  "bto_id": "BTO:0000759",
  "caloha_id": "TS-0564",
  "efo_id": "EFO:0000887",
  "uberon_id": "UBERON:0002107"
}
```

`tissue_chembl_id` is still accepted as a legacy source alias, but the active
normalized contract publishes this field as `tissue_id`.

### Silver (нормализованный)

| tissue_id | pref_name | bto_id | uberon_id |
|-----------|-----------|--------|-----------|
| CHEMBL3638186 | Liver | BTO:0000759 | UBERON:0002107 |

---

*Последнее обновление: 2026-03-03*
