______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Class Diagram: 10 Adapters

- Исходная диаграмма: `class-diagrams/10-adapters.mmd`

## Описание

Диаграмма Infrastructure Adapters показывает архитектурный срез семейства `bioetl.infrastructure.adapters` и фиксирует ключевые контракты, роли и отношения внутри HTTP adapter hierarchy. Её следует читать как representative view: схема покрывает базовые адаптеры, mixin-композицию, `UnifiedHTTPClient`, decorator layer и набор показательных provider adapters, но не претендует на роль исчерпывающего инвентаря всех инфраструктурных реализаций.

**Ключевые элементы:**

- **Mixins**: HealthCheckMixin, HealthCheckProviderMixin — переиспользуемые поведения
- **Base Adapters**: BaseHttpAdapter, BaseSyncAdapter — базовые классы с core функциональностью
- **HTTP Client**: UnifiedHTTPClient — сконцентрирована логика rate limiting, circuit breaker, retry
- **Decorators**: CircuitBreakerDataSourceDecorator, RetryingDataSourceDecorator, CachedBronzeDataSource — оборачивают DataSourcePort для добавления cross-cutting concerns (resilience, caching). RetryingDataSourceDecorator использует delegation pattern с __post_init__ для создания private aliases (\_data_source, \_retry_config, \_logger, \_metrics) обеспечивая compliance с NAME-004 (private attribute underscore prefix)
- **Provider Adapters**: ChemblAdapter, PubMedAdapter, UniProtAdapter и др. — конкретные реализации для каждого провайдера

## Метаданные

- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата метаданных: `2026-03-20` (обновлено: описание переведено в режим representative architectural slice)
- Версия диаграммы: `1.2.0`
