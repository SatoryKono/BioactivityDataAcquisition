# PipelineBase

**Модуль:** `src/bioetl/core/pipeline_base.py`

`PipelineBase` — это абстрактный базовый класс для всех табличных ETL-пайплайнов в проекте. Он инкапсулирует общую логику оркестрации, управления ресурсами, валидации и записи.

## Назначение

1. **Оркестрация**: Обеспечивает последовательный запуск стадий `extract`, `transform`, `validate`, `write`.
2. **Ресурсы**: Управляет жизненным циклом клиентов (регистрация, закрытие соединений).
3. **Надежность**: Гарантирует атомарную запись результатов.
4. **Наблюдаемость**: Интегрирует логирование и метрики.

## Публичный интерфейс

### `run`

```python
def run(
    self,
    output_path: Path,
    *args,
    dry_run: bool = False,
    **kwargs
) -> RunResult:
    """
    Запускает полный цикл ETL-пайплайна.

    Args:
        output_path: Путь к директории для сохранения результатов.
        dry_run: Если True, стадия write пропускается.

    Returns:
        RunResult с информацией о выполнении.
    """
```

### `extract` (Abstract)

```python
@abstractmethod
def extract(self, *args, **kwargs) -> pd.DataFrame:
    """
    Извлекает данные из источника.
    Должен возвращать сырой DataFrame.
    """
```

### `transform` (Abstract)

```python
@abstractmethod
def transform(self, df: pd.DataFrame) -> pd.DataFrame:
    """
    Преобразует сырые данные в нормализованный вид.
    Очистка, приведение типов, обогащение.
    """
```

### `validate`

```python
def validate(self, df: pd.DataFrame) -> pd.DataFrame:
    """
    Валидирует DataFrame по Pandera-схеме.
    Вызывает SchemaRegistry для получения схемы.
    """
```

### `write`

```python
def write(self, df: pd.DataFrame, output_path: Path) -> WriteResult:
    """
    Записывает валидированный DataFrame на диск.
    Использует атомарную запись и генерирует метаданные.
    """
```

### `register_client`

```python
def register_client(self, name: str, client: Any) -> None:
    """
    Регистрирует клиент для автоматического закрытия ресурсов в конце работы.
    """
```

## Внутренние методы

### `_add_hash_columns`

```python
def _add_hash_columns(self, df: pd.DataFrame) -> pd.DataFrame:
    """
    Добавляет колонки hash_row (SHA256 всей строки) и hash_business_key.
    Используется для детерминизма и версионирования.
    """
```

