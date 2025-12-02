# 02 Architecture Overview

## Шестислойная модель
- **Orchestration** — управление запуском пайплайнов, профили конфигурации, хуки жизненного цикла.
- **Monitoring** — логирование, метрики, прогресс, трассировка ошибок.
- **Client** — единый доступ к внешним API через UnifiedAPIClient и специализированные клиенты.
- **Transform** — нормализация, очистка, вычисление хешей, подготовка к валидации.
- **Validation** — проверка данных через SchemaRegistry и ValidationService, политики обработки ошибок.
- **Output** — атомарная запись таблиц и артефактов через UnifiedOutputWriter.

## Центральные абстракции
- `PipelineBase` — каркас пайплайна с методами extract/transform/validate/write.
- ABC-интерфейсы слоёв (клиенты, трансформеры, валидаторы, писатели) для единообразия контрактов.
- `UnifiedAPIClient`, `UnifiedOutputWriter`, `SchemaRegistry`, `ValidationService` — общие сервисы, доступные всем пайплайнам.

## Поток данных
1. **extract**: клиент получает данные из внешнего API.
2. **transform**: данные нормализуются и дополняются служебными колонками.
3. **validate**: применяется схема, ошибки обрабатываются политиками.
4. **write**: таблицы и метаданные пишутся атомарно.

## Навигация
- Детали архитектуры: `docs/architecture/*`.
- Справочники ABC и ядра: `docs/domain/abc/00-index.md`, `docs/infrastructure/core/*`.
- Описание пайплайнов: `docs/application/pipelines/chembl/00-index.md`.
- Практические гайды: `docs/guides/00-running-pipelines.md`.
