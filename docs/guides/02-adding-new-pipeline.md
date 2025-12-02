# 02 Adding New Pipeline

## Шаги
1. **Клиент источника**: реализуйте ABC/Default/Impl для нового API (contracts.py, factories.py, impl/*), добавьте в abc реестры.
2. **Схема**: создайте Pandera-схему для целевой сущности и зарегистрируйте её в SchemaRegistry.
3. **Пайплайн-класс**: унаследуйте PipelineBase или соответствующий базовый класс провайдера (например, ChemblPipelineBase), определите extract/transform/validate/write.
4. **Конфигурация**: добавьте YAML в `configs/pipelines/<provider>/<entity>.yaml` с профилями base/dev/prod.
5. **CLI-команда**: зарегистрируйте новую команду через CLICommandABC для запуска пайплайна.
6. **Документация**: обновите соответствующие файлы в `docs/application/pipelines/<provider>/<entity>/` и справочники ABC.

## Использование паттерна ABC/Default/Impl
Следуйте политике: новый ABC → Default (может быть stub) → Impl. Обновите `abc_registry.yaml` и `abc_impls.yaml` для привязки реализаций. Докстринги ABC должны описывать интерфейс и ссылки на Default/Impl.

## Примеры
Ориентируйтесь на ChEMBL пайплайны в `docs/application/pipelines/chembl/*` и кодовые реализации в `src/bioetl/pipelines/chembl`. Переиспользуйте общие сервисы (UnifiedAPIClient, ValidationService, UnifiedOutputWriter).
