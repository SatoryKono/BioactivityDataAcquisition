# Пайплайн: ChEMBL Molecule

**Имя пайплайна:** `chembl_molecule`
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
| `molecule_id` | `str` | Уникальный ChEMBL ID (например, `CHEMBL25`) |
| `pref_name` | `str` | Предпочтительное название |
| `max_phase` | `int` | Максимальная фаза клинических испытаний (0-4) |
| `molecule_type` | `str` | Тип молекулы (Small molecule, Protein, etc.) |

### Структурные данные

| Поле | Тип | Описание |
|------|-----|----------|
| `canonical_smiles` | `str` | Каноническая SMILES-формула |
| `standard_inchi` | `str` | Стандартный InChI |
| `inchi_key` | `str` | Ключ InChI |

### Физико-химические свойства

| Поле | Тип | Описание |
|------|-----|----------|
| `logp` | `float` | Расчётный LogP |
| `mw_freebase` | `float` | Молекулярная масса свободного основания |
| `molecular_weight` | `float` | Полная молекулярная масса |
| `hba_count` | `int` | Акцепторы водородных связей |
| `hbd_count` | `int` | Доноры водородных связей |
| `polar_surface_area` | `float` | Полярная площадь поверхности |
| `rotatable_bond_count` | `int` | Вращающиеся связи |
| `ro5_violation_count` | `int` | Нарушения правила Липински |
| `heavy_atom_count` | `int` | Тяжёлые атомы |
| `aromatic_ring_count` | `int` | Ароматические кольца |
| `qed_score` | `float` | QED (drug-likeness) |

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
- `molecule_properties` → канонические поля свойств (`logp`, `molecular_weight`, и т.д.)
- `molecule_structures` → структурные поля (`canonical_smiles`, `standard_inchi`, `inchi_key`)

### Entity ID

```python
entity_id = f"chembl:{molecule_id}"
```

---

## 4. Валидация

### DQ-правила

1. **`molecule_id`** — обязательное, regex `^CHEMBL\d+$`
2. **`canonical_smiles`** — рекомендуется для анализа

### Пороги ошибок

| Порог | Условие | Действие |
|-------|---------|----------|
| Soft | > 5% ошибок | WARNING |
| Hard | > 20% ошибок | FAIL BATCH |

---

## 5. Использование CLI

```bash
# Инкрементальная загрузка
bioetl run --pipeline chembl_molecule

# С ограничением
bioetl run --pipeline chembl_molecule --limit 1000

# Полная перезагрузка
bioetl run --pipeline chembl_molecule --run-type rebuild
```

---

## 6. Связанные файлы

| Компонент | Путь |
|-----------|------|
| Конфигурация | `configs/entities/chembl/molecule.yaml` |
| Трансформер | `src/bioetl/application/pipelines/chembl/molecule_transformer.py` |
| Сущность | `src/bioetl/domain/entities/chembl_structures_molecules.py` |

---

*Последнее обновление: 2026-03-03*
