# Adding New Pipeline

Пошаговое руководство по добавлению нового ETL-пайплайна.

## Шаг 1. Клиент (если новый источник)
Если источник данных еще не поддерживается, реализуйте наследника `BaseClient`.

```python
# src/bioetl/clients/newsource/client.py
class NewSourceClient(BaseClient):
    def request_entity(self, **filters):
        ...
```

## Шаг 2. Схема данных
Опишите структуру данных с помощью Pandera.

```python
# src/bioetl/schemas/newsource/entity_schema.py
class EntitySchema(pa.DataFrameModel):
    id: Series[int] = pa.Field(ge=1)
    name: Series[str]
```

## Шаг 3. Класс Пайплайна
Создайте класс пайплайна, унаследованный от `PipelineBase`.

```python
# src/bioetl/pipelines/newsource/entity/run.py
class NewSourceEntityPipeline(PipelineBase):
    def extract(self) -> pd.DataFrame:
        return self.client.fetch_all()

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        # Логика нормализации
        return df
```

## Шаг 4. Конфигурация
Создайте YAML-файл.

```yaml
# configs/pipelines/newsource/entity.yaml
extends: base_default
entity_name: entity
endpoint: /entity
```

## Шаг 5. Регистрация в CLI
Добавьте команду в CLI.

```python
# src/bioetl/cli/commands/newsource.py
@app.command()
def entity_newsource(...):
    # Запуск пайплайна
```

## Шаг 6. Тестирование
Запустите smoke-тест.

```bash
bioetl run entity_newsource --profile development --dry-run
```

