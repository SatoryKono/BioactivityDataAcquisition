# TestItem ChEMBL Pipeline

**Сущность:** TestItem (Molecule)
**Endpoint:** `/molecule`
**Класс:** `ChemblTestitemPipeline`

## Описание
Извлекает данные о тестируемых химических соединениях.

## Трансформация

**Класс:** `TestitemTransformer`

- Извлечение химических дескрипторов (SMILES, InChIKey) из структуры `molecule_structures`.
- Обработка синонимов и торговых названий.

## Схема

**Схема:** `TestitemSchema`

Валидирует химические идентификаторы и фазу клинических испытаний.

