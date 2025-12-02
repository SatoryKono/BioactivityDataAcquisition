# 03 Circuit Breaker

## Описание

`CircuitBreakerImpl` — реализация шаблона Circuit Breaker для устойчивости HTTP-запросов. Отслеживает число ошибок, открывает "предохранитель" при достижении порога и автоматически сбрасывается по таймеру.

## Модуль

`src/bioetl/core/http/circuit_breaker.py`

## Наследование

Circuit Breaker реализует интерфейс `CircuitBreakerStrategyABC` и предоставляет реализацию паттерна Circuit Breaker.

## Состояния Circuit Breaker

1. **Closed (Закрыт)**: нормальная работа, запросы выполняются
2. **Open (Открыт)**: слишком много ошибок, запросы блокируются
3. **Half-Open (Полуоткрыт)**: тестирование восстановления, ограниченные запросы

## Основные методы

### `before_call(self) -> None`

Вызывается перед выполнением запроса. Проверяет состояние Circuit Breaker и выбрасывает исключение, если предохранитель открыт.

### `record_success(self) -> None`

Записывает успешное выполнение запроса. Может перевести Circuit Breaker из состояния Half-Open в Closed.

### `record_failure(self) -> None`

Записывает неудачное выполнение запроса. Может перевести Circuit Breaker из состояния Closed в Open при достижении порога ошибок.

### `call(self, func: Callable[[], Response]) -> Response`

Выполняет функцию с защитой Circuit Breaker.

**Параметры:**
- `func` — функция для выполнения (возвращает Response)

**Возвращает:** ответ от функции.

**Процесс:**
1. Проверка состояния перед вызовом
2. Выполнение функции
3. Запись результата (успех/ошибка)
4. Обновление состояния Circuit Breaker

## Автоматический сброс

Circuit Breaker автоматически переходит в состояние Half-Open по истечении таймера, что позволяет тестировать восстановление сервиса.

## Related Components

- **CircuitBreakerStrategyABC**: интерфейс стратегии Circuit Breaker
- **RequestsBackend**: может использовать Circuit Breaker для защиты от сбоев (см. `docs/02-pipelines/chembl/common/03-chembl-requests-backend.md`)

