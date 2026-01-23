# API Reference

Документация API сформирована по docstring’ам модулей и публичных классов.

## Слои

### Domain

Доменный слой содержит сущности, value objects, порты и контекстные объекты, а также публичный API для портов, типов, исключений, конфигураций, фильтров и чистых доменных трансформаций.

### Application

Слой приложения отвечает за оркестрацию пайплайнов.

### Infrastructure

Инфраструктурный слой предоставляет реализации доменных портов, включая HTTP-адаптеры, хранилище, блокировки и экспорт метрик.

### Composition

Слой композиции — единственная точка сборки зависимостей в архитектуре Ports & Adapters; включает bootstrap, registry, builders, типы, observability и entrypoints.

## Разделы

- [Application](application.md)
- [Application Core](application/core.md)
- [Composition Factories](composition/factories.md)
