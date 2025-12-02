# 04 Pagination Strategy

## Описание

`DefaultPaginationStrategy` — простая стратегия постраничной навигации по API. Использует параметр "page" и поле ответа "next" для последовательного получения всех страниц результатов.

## Модуль

`src/bioetl/core/http/pagination.py`

## Наследование

Стратегия реализует интерфейс `PaginatorABC` и предоставляет базовую реализацию пагинации.

## Алгоритм пагинации

Стратегия работает следующим образом:
1. Выполняет начальный запрос с параметром `page=1`
2. Извлекает поле `next` из ответа
3. Выполняет запросы для следующих страниц до тех пор, пока `next` не станет `None`

## Основной метод

### `iter_pages(self, initial_response: Mapping[str, Any] | Sequence[Mapping[str, Any]], transport: ApiTransportProtocol, *, endpoint: str, params: Mapping[str, Any] | None = None, logger: Any | None = None, page_key: str | None = None, next_key: str | None = None, page_param: str | None = None, normalize: Any | None = None) -> Iterator[ResponsePayload]`

Итерирует по страницам результатов API.

**Параметры:**
- `initial_response` — начальный ответ от API
- `transport` — транспортный протокол для выполнения запросов
- `endpoint` — endpoint API
- `params` — параметры запроса (опционально)
- `logger` — логгер для записи событий (опционально)
- `page_key` — ключ для извлечения номера страницы из ответа (опционально)
- `next_key` — ключ для извлечения следующей страницы из ответа (опционально)
- `page_param` — имя параметра для номера страницы (по умолчанию "page")
- `normalize` — функция нормализации ответа (опционально)

**Возвращает:** итератор по страницам результатов.

## Настройка ключей

Стратегия позволяет настроить:
- Ключ для извлечения номера страницы
- Ключ для извлечения следующей страницы
- Имя параметра запроса для номера страницы

## Related Components

- **PaginatorABC**: интерфейс стратегии пагинации (см. `docs/01-ABC/12-paginator-abc.md`)
- **UnifiedAPIClient**: использует стратегию для пагинации (см. `docs/02-pipelines/03-unified-api-client.md`)

