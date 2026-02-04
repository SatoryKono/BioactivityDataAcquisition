# Пайплайн: ChEMBL Target Component

**Имя пайплайна:** `chembl_target_component`
**Провайдер:** `chembl`
**Сущность:** `target_component`
**Версия схемы:** 1.0.0

---

## 1. Описание

Пайплайн извлекает данные о компонентах мишеней из API ChEMBL. Компоненты мишеней — это отдельные белки или субъединицы, входящие в состав сложных мишеней.

---

## 2. Ключевые поля

### Идентификаторы

| Поле | Тип | Описание |
|------|-----|----------|
| `component_id` | `int` | Уникальный ID компонента |
| `accession` | `str` | UniProt accession |
| `component_type` | `str` | Тип компонента (PROTEIN, etc.) |

### Описание

| Поле | Тип | Описание |
|------|-----|----------|
| `component_description` | `str` | Описание компонента |
| `sequence` | `str` | Аминокислотная последовательность |

### Таксономия

| Поле | Тип | Описание |
|------|-----|----------|
| `organism` | `str` | Организм |
| `tax_id` | `int` | NCBI Taxonomy ID |

### Классификация белков

| Поле | Тип | Описание |
|------|-----|----------|
| `protein_classifications` | `list[dict]` | Классификация по ChEMBL |

---

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/chembl/target_component_transformer.py`

### Entity ID

```python
entity_id = f"chembl:component_{component_id}"
```

---

## 4. Использование CLI

```bash
# Инкрементальная загрузка
bioetl run chembl_target_component

# С ограничением
bioetl run chembl_target_component --limit 500
```

---

## 5. Связанные файлы

| Компонент | Путь |
|-----------|------|
| Конфигурация | `configs/pipelines/chembl/target_component.yaml` |
| Трансформер | `src/bioetl/application/pipelines/chembl/target_component_transformer.py` |

---

*Последнее обновление: 2025-12-27*
