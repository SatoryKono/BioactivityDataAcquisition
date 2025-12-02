# Target ChEMBL Pipeline

**Сущность:** Target
**Endpoint:** `/target`
**Класс:** `ChemblTargetPipeline`

## Описание
Извлекает информацию о биологических мишенях.

## Трансформация

**Класс:** `TargetTransformer`

- Извлечение `uniprot_id` из вложенных структур JSON (если API отдает вложенность).
- Нормализация названия мишени (`pref_name`).

## Схема

**Схема:** `TargetSchema`

Проверяет наличие `target_chembl_id` и типа мишени.

