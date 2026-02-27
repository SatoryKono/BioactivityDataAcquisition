# Пайплайн: ChEMBL Target Component

**Имя пайплайна:** `chembl-target-component`
**Провайдер:** `chembl`
**Сущность:** `target-component`
**Версия схемы:** 1.2.0

---

## 1. Описание

Пайплайн извлекает данные о компонентах мишеней из API ChEMBL. Компоненты мишеней — это отдельные белки или субъединицы, входящие в состав сложных мишеней.

---

## 2. Ключевые поля

### Идентификаторы

| Поле | Тип | Описание |
|------|-----|----------|
| `component-id` | `int` | Уникальный ID компонента |
| `accession` | `str` | UniProt accession |
| `component-type` | `str` | Тип компонента (PROTEIN, etc.) |

### Описание

| Поле | Тип | Описание |
|------|-----|----------|
| `component-description` | `str` | Описание компонента |
| `sequence` | `str` | Аминокислотная последовательность |

### Таксономия

| Поле | Тип | Описание |
|------|-----|----------|
| `organism` | `str` | Организм |
| `tax-id` | `int` | NCBI Taxonomy ID |

### Классификация белков

| Поле | Тип | Описание |
|------|-----|----------|
| `protein-classifications` | `list[dict]` | Классификация по ChEMBL |

---

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/chembl/target-component-transformer.py`

### Entity ID

```python
entity-id = f"chembl:component-{component-id}"
```

---

## 4. Использование CLI

```bash
# Инкрементальная загрузка
bioetl run chembl-target-component

# С ограничением
bioetl run chembl-target-component --limit 500
```

---

## 5. Связанные файлы

| Компонент | Путь |
|-----------|------|
| Конфигурация | `configs/entities/chembl/target-component.yaml` |
| Трансформер | `src/bioetl/application/pipelines/chembl/target-component-transformer.py` |

---

*Последнее обновление: 2025-12-27*
