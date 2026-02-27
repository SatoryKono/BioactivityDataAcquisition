# Пайплайн: ChEMBL Molecule

**Имя пайплайна:** `chembl-molecule`
**Провайдер:** `chembl`
**Сущность:** `molecule`
**Версия схемы:** 1.2.0

---

## 1. Описание

Пайплайн извлекает данные о химических соединениях из API ChEMBL. Каждая запись содержит информацию о структуре молекулы, физико-химических свойствах и идентификаторах.

---

## 2. Ключевые поля

### Идентификаторы

| Поле | Тип | Описание |
|------|-----|----------|
| `molecule-chembl-id` | `str` | Уникальный ChEMBL ID (например, `CHEMBL25`) |
| `pref-name` | `str` | Предпочтительное название |
| `max-phase` | `int` | Максимальная фаза клинических испытаний (0-4) |
| `molecule-type` | `str` | Тип молекулы (Small molecule, Protein, etc.) |

### Структурные данные

| Поле | Тип | Описание |
|------|-----|----------|
| `structure-canonical-smiles` | `str` | Каноническая SMILES-формула |
| `structure-standard-inchi` | `str` | Стандартный InChI |
| `structure-standard-inchi-key` | `str` | Ключ InChI |

### Физико-химические свойства

| Поле | Тип | Описание |
|------|-----|----------|
| `property-alogp` | `float` | Расчётный LogP |
| `property-mw-freebase` | `float` | Молекулярная масса свободного основания |
| `property-full-mwt` | `float` | Полная молекулярная масса |
| `property-hba` | `int` | Акцепторы водородных связей |
| `property-hbd` | `int` | Доноры водородных связей |
| `property-psa` | `float` | Полярная площадь поверхности |
| `property-rtb` | `int` | Вращающиеся связи |
| `property-ro5-violations` | `int` | Нарушения правила Липински |
| `property-heavy-atoms` | `int` | Тяжёлые атомы |
| `property-aromatic-rings` | `int` | Ароматические кольца |
| `property-qed-weighted` | `float` | QED (drug-likeness) |

### Иерархия

| Поле | Тип | Описание |
|------|-----|----------|
| `hierarchy-parent-chembl-id` | `str` | ID родительской молекулы |
| `hierarchy-active-chembl-id` | `str` | ID активной формы |
| `hierarchy-child-chembl-id` | `str` | ID дочерней молекулы |

---

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/chembl/molecule-transformer.py`

### Развёртывание вложенных структур

- `molecule-hierarchy` → `hierarchy-*` поля
- `molecule-properties` → `property-*` поля
- `molecule-structures` → `structure-*` поля

### Entity ID

```python
entity-id = f"chembl:{molecule-chembl-id}"
```

---

## 4. Валидация

### DQ-правила

1. **`molecule-chembl-id`** — обязательное, regex `^CHEMBL\d+$`
2. **`structure-canonical-smiles`** — рекомендуется для анализа

### Пороги ошибок

| Порог | Условие | Действие |
|-------|---------|----------|
| Soft | > 5% ошибок | WARNING |
| Hard | > 20% ошибок | FAIL BATCH |

---

## 5. Использование CLI

```bash
# Инкрементальная загрузка
bioetl run chembl-molecule

# С ограничением
bioetl run chembl-molecule --limit 1000

# Полная перезагрузка
bioetl run chembl-molecule --run-type rebuild
```

---

## 6. Связанные файлы

| Компонент | Путь |
|-----------|------|
| Конфигурация | `configs/entities/chembl/molecule.yaml` |
| Трансформер | `src/bioetl/application/pipelines/chembl/molecule-transformer.py` |
| Сущность | `src/bioetl/domain/entities.py` |

---

*Последнее обновление: 2025-12-27*
