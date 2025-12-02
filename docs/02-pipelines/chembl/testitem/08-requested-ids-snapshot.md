# 08 Requested IDs Snapshot

## Описание

`RequestedIdsSnapshot` — утилитный класс для накопления запрошенных ChEMBL-идентификаторов тестовых элементов без перегрузки памяти. Сохраняет ID во временный файл с последовательной выдачей.

## Модуль

`src/bioetl/library/pipelines/testitem/cli.py`

## Наследование

Класс наследуется от `Sequence[str]` и реализует интерфейс последовательности для работы с идентификаторами.

## Основные методы

### `__len__(self) -> int`

Возвращает количество накопленных идентификаторов.

### `__iter__(self) -> Iterator[str]`

Возвращает итератор по идентификаторам для последовательной обработки.

### `__getitem__(self, index: int) -> str`

Возвращает идентификатор по индексу (реализация абстрактного метода `Sequence`).

### `append(self, item_id: str) -> None`

Добавляет идентификатор в snapshot, сохраняя его во временный файл.

### `finish(self) -> None`

Завершает накопление идентификаторов и подготавливает snapshot для чтения.

### `iter_for_fetch(self) -> Iterator[str]`

Возвращает итератор для последовательной выдачи идентификаторов при извлечении данных.

## Внутренние методы

### `_ensure_writer(self) -> None`

Обеспечивает наличие открытого writer для записи идентификаторов во временный файл.

### `_read_from_disk(self) -> list[str]`

Читает идентификаторы с диска из временного файла.

### `_iterate_all(self) -> Iterator[str]`

Итерирует по всем идентификаторам из временного файла.

### `_cleanup_path(self) -> None`

Очищает временный файл после использования.

## Использование

Класс используется для накопления большого количества идентификаторов без загрузки их всех в память:

```python
from bioetl.library.pipelines.testitem.cli import RequestedIdsSnapshot

snapshot = RequestedIdsSnapshot()
snapshot.append("CHEMBL1")
snapshot.append("CHEMBL2")
snapshot.finish()

for item_id in snapshot.iter_for_fetch():
    # Обработка идентификатора
    process_item(item_id)
```

## Преимущества

- Экономия памяти при работе с большими наборами идентификаторов
- Последовательная обработка без загрузки всех ID в память
- Автоматическая очистка временных файлов

## Related Components

- **TestitemPipelineOptions**: параметры пайплайна (см. `docs/02-pipelines/chembl/testitem/03-testitem-pipeline-options.md`)
- **TestItemChemblPipeline**: основной пайплайн (см. `docs/02-pipelines/chembl/testitem/00-testitem-chembl-overview.md`)

