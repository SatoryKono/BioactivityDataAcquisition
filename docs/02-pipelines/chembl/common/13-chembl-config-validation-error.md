# 13 ChEMBL Config Validation Error

## Описание

`ConfigValidationError` — исключение, выбрасываемое при некорректной пользовательской конфигурации пайплайна. Используется для сигнализации о неверных параметрах в настройках (например, неподдерживаемое значение режима, отсутствие обязательных полей сортировки и т.д.), прерывая выполнение пайплайна с сообщением об ошибке.

## Модуль

`src/bioetl/pipelines/chembl/common/descriptor.py`

## Наследование

Исключение наследуется от `ValueError` и предоставляет специфичную для конфигурации обработку ошибок.

## Использование

Исключение выбрасывается при:

- Неподдерживаемых значениях режима работы
- Отсутствии обязательных полей конфигурации
- Некорректных параметрах сортировки
- Других ошибках валидации конфигурации

## Пример

```python
if mode not in ("chembl", "all"):
    raise ConfigValidationError(f"Unsupported mode: {mode}")
```

## Related Components

- **ChemblBasePipeline**: использует исключение для валидации конфигурации (см. `docs/02-pipelines/chembl/common/05-chembl-base-pipeline.md`)
- **ChemblExtractionDescriptor**: использует исключение при валидации дескриптора (см. `docs/02-pipelines/chembl/activity/00-activity-chembl-overview.md` - раздел Extraction Descriptor)

