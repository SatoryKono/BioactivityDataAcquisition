# Assay ChEMBL Pipeline

**Сущность:** Assay
**Endpoint:** `/assay`
**Класс:** `ChemblAssayPipeline`

## Описание
Извлекает каталог биологических экспериментов.

## Трансформация

**Класс:** `AssayTransformer`

- Нормализация поля `assay_type` (приведение к верхнему регистру).
- Очистка описания (`description`) от спецсимволов.

## Схема

**Схема:** `AssaySchema`

Валидирует формат `assay_chembl_id` (Regex `^CHEMBL\d+$`) и допустимые значения `assay_type`.

