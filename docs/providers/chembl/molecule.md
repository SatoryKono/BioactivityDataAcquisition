# Пайплайн: ChEMBL Molecule

**Имя пайплайна:** `chembl_molecule`
**Провайдер:** `chembl`
**Сущность:** `molecule`
**Версия схемы:** 1.0.0

---

## 1. Описание

Пайплайн извлекает данные о химических соединениях из API ChEMBL. Каждая запись содержит информацию о структуре молекулы, физико-химических свойствах и идентификаторах.

---

## 2. Ключевые поля

### Идентификаторы

| Поле | Тип | Описание |
|------|-----|----------|
| `molecule_chembl_id` | `str` | Уникальный ChEMBL ID (например, `CHEMBL25`) |
| `pref_name` | `str` | Предпочтительное название |
| `max_phase` | `int` | Максимальная фаза клинических испытаний (0-4) |
| `molecule_type` | `str` | Тип молекулы (Small molecule, Protein, etc.) |

### Структурные данные

| Поле | Тип | Описание |
|------|-----|----------|
| `structure_canonical_smiles` | `str` | Каноническая SMILES-формула |
| `structure_standard_inchi` | `str` | Стандартный InChI |
| `structure_standard_inchi_key` | `str` | Ключ InChI |

### Физико-химические свойства

| Поле | Тип | Описание |
|------|-----|----------|
| `property_alogp` | `float` | Расчётный LogP |
| `property_mw_freebase` | `float` | Молекулярная масса свободного основания |
| `property_full_mwt` | `float` | Полная молекулярная масса |
| `property_hba` | `int` | Акцепторы водородных связей |
| `property_hbd` | `int` | Доноры водородных связей |
| `property_psa` | `float` | Полярная площадь поверхности |
| `property_rtb` | `int` | Вращающиеся связи |
| `property_ro5_violations` | `int` | Нарушения правила Липински |
| `property_heavy_atoms` | `int` | Тяжёлые атомы |
| `property_aromatic_rings` | `int` | Ароматические кольца |
| `property_qed_weighted` | `float` | QED (drug-likeness) |

### Иерархия

| Поле | Тип | Описание |
|------|-----|----------|
| `hierarchy_parent_chembl_id` | `str` | ID родительской молекулы |
| `hierarchy_active_chembl_id` | `str` | ID активной формы |
| `hierarchy_child_chembl_id` | `str` | ID дочерней молекулы |

---

## 3. Трансформация

**Файл:** `src/bioetl/application/pipelines/chembl/molecule_transformer.py`

### Развёртывание вложенных структур

- `molecule_hierarchy` → `hierarchy_*` поля
- `molecule_properties` → `property_*` поля
- `molecule_structures` → `structure_*` поля

### Entity ID

```python
entity_id = f"chembl:{molecule_chembl_id}"
```

---

## 4. Валидация

### DQ-правила

1. **`molecule_chembl_id`** — обязательное, regex `^CHEMBL\d+$`
2. **`structure_canonical_smiles`** — рекомендуется для анализа

### Пороги ошибок

| Порог | Условие | Действие |
|-------|---------|----------|
| Soft | > 5% ошибок | WARNING |
| Hard | > 20% ошибок | FAIL BATCH |

---

## 5. Использование CLI

```bash
# Инкрементальная загрузка
bioetl run chembl_molecule

# С ограничением
bioetl run chembl_molecule --limit 1000

# Полная перезагрузка
bioetl run chembl_molecule --run-type rebuild
```

---

## 6. Связанные файлы

| Компонент | Путь |
|-----------|------|
| Конфигурация | `configs/pipelines/chembl/molecule.yaml` |
| Трансформер | `src/bioetl/application/pipelines/chembl/molecule_transformer.py` |
| Сущность | `src/bioetl/domain/entities.py` |

---

*Последнее обновление: 2025-12-27*
