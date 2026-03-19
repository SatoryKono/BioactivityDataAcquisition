# Class Diagram: 10 Adapters

- Исходная диаграмма: `class-diagrams/10-adapters.mmd`

## Описание
Диаграмма Infrastructure Adapters показывает архитектурную модель модуля `10-adapters` и фиксирует контракты, роли и отношения между сущностями слоя `Class / Interface`. Основной фокус: HTTP adapter class hierarchy with mixins. На схеме отражено примерно 18 классов и 14 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга.

**Ключевые элементы:**
- **Mixins**: HealthCheckMixin, HealthCheckProviderMixin — переиспользуемые поведения
- **Base Adapters**: BaseHttpAdapter, BaseSyncAdapter — базовые классы с core функциональностью
- **HTTP Client**: UnifiedHTTPClient — сконцентрирована логика rate limiting, circuit breaker, retry
- **Decorators**: CircuitBreakerDataSourceDecorator, RetryingDataSourceDecorator, CachedBronzeDataSource — оборачивают DataSourcePort для добавления cross-cutting concerns (resilience, caching). RetryingDataSourceDecorator использует delegation pattern с __post_init__ для создания private aliases (_data_source, _retry_config, _logger, _metrics) обеспечивая compliance с NAME-004 (private attribute underscore prefix)
- **Provider Adapters**: ChemblAdapter, PubMedAdapter, UniProtAdapter и др. — конкретные реализации для каждого провайдера

## Метаданные
- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата метаданных: `2026-03-08` (обновлено: добавлены детали RetryingDataSourceDecorator с delegation pattern)
- Версия диаграммы: `1.2.0`
