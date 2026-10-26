# Аудит обработки CancelledError в application-слое (APP-001)

## 1. `src/bioetl/application/services/run_reports/composite.py`
* **Ревизия (SHA):** `f07ead17df6283b9a7d2d8bfc7e10e2358f97c8b`
* **Метод/команда:** `grep -n -C 20 "CancelledError" src/bioetl/application/services/run_reports/composite.py`
* **Результат:**
  * В методе `write` обрабатывается `error`.
  * Если `error` является экземпляром `asyncio.CancelledError` (или `PipelineShutdownError`), статус (`status`) устанавливается в `"shutdown"`.
  * Количественное утверждение: **MEASURED** (1 обработчик).
  * Блокировки отсутствуют.

## 2. `src/bioetl/application/services/execution/pipeline_runner_service.py`
* **Ревизия (SHA):** `f07ead17df6283b9a7d2d8bfc7e10e2358f97c8b`
* **Метод/команда:** `grep -n -C 20 "CancelledError" src/bioetl/application/services/execution/pipeline_runner_service.py`
* **Результат:**
  * В методе `_execute_prepared_run` есть блок `except asyncio.CancelledError:`.
  * При возникновении ошибки создается `PipelineExecutionResult` со статусом `"shutdown"` и `error_type="CancelledError"`.
  * Если `runner is not None`, формируется полноценный `RunResult`, иначе создается `RunResult` напрямую со статусом `SHUTDOWN`.
  * Записывается событие аудита со статусом `"shutdown"` и `error_type="CancelledError"`.
  * Затем вызывается `self._finalize_report(result, options)` и исключение пробрасывается дальше (`raise`).
  * Количественное утверждение: **MEASURED** (1 обработчик `except asyncio.CancelledError:`).
  * Блокировки отсутствуют.

## 3. `src/bioetl/application/core/runner.py`
* **Ревизия (SHA):** `f07ead17df6283b9a7d2d8bfc7e10e2358f97c8b`
* **Метод/команда:** `grep -n -C 20 "CancelledError" src/bioetl/application/core/runner.py`
* **Результат:**
  * В методе `run` есть блок `except (PipelineShutdownError, CancelledError) as exc:`.
  * Устанавливается `debug_export_status = "shutdown"`.
  * Вызывается `self._record_terminal_shutdown()`.
  * Если `exc` является экземпляром `CancelledError`, исключение пробрасывается дальше (`raise`).
  * Количественное утверждение: **MEASURED** (1 обработчик `except (PipelineShutdownError, CancelledError):`).
  * Блокировки отсутствуют.

## 4. `src/bioetl/application/core/batch_execution/run_service.py`
* **Ревизия (SHA):** `f07ead17df6283b9a7d2d8bfc7e10e2358f97c8b`
* **Метод/команда:** `grep -n -C 20 "CancelledError" src/bioetl/application/core/batch_execution/run_service.py`
* **Результат:**
  * В методе `_run_with_finalization_policy` есть блок `except asyncio.CancelledError:`.
  * Обработка: создается отдельная задача (`asyncio.create_task`) для выполнения финализации `self._finalize(..., shutdown=True)`.
  * Финализация оборачивается в `asyncio.shield`, чтобы повторная отмена не прервала сохранение контрольной точки или спанов.
  * Внутри есть вложенный `try...except asyncio.CancelledError:`, который дожидается завершения задачи финализации (`await finalize_task`) и пробрасывает исходную ошибку `CancelledError`.
  * Внешний блок также пробрасывает `CancelledError` (`raise`).
  * Количественное утверждение: **MEASURED** (2 обработчика `except asyncio.CancelledError:`).
  * Блокировки отсутствуют.

## 5. `src/bioetl/application/core/derived_scan_budget.py`
* **Ревизия (SHA):** `f07ead17df6283b9a7d2d8bfc7e10e2358f97c8b`
* **Метод/команда:** `grep -n -C 20 "CancelledError" src/bioetl/application/core/derived_scan_budget.py`
* **Результат:**
  * В методе `_cancel_scan_pending` есть блок `except (asyncio.CancelledError, StopAsyncIteration, TimeoutError):`.
  * Исключение `CancelledError` игнорируется (`pass`), не пробрасывается, позволяя отменить ожидающую задачу сканирования без "всплытия" ошибки в вызывающий код.
  * Количественное утверждение: **MEASURED** (1 обработчик).
  * Блокировки отсутствуют.

## 6. `src/bioetl/application/core/pipeline_services.py`
* **Ревизия (SHA):** `f07ead17df6283b9a7d2d8bfc7e10e2358f97c8b`
* **Метод/команда:** `grep -n -C 20 "CancelledError" src/bioetl/application/core/pipeline_services.py`
* **Результат:**
  * В методе `aclose` при обработке результатов `asyncio.gather(*io_tasks, return_exceptions=True)` перебираются результаты.
  * Если `result` является исключением, происходит проверка `if isinstance(result, asyncio.CancelledError) and cancelled is None:`.
  * Ошибка `CancelledError` перехватывается, сохраняется в переменную `cancelled`, и в конце метода пробрасывается (`raise cancelled`) с логгированием предупреждения "Pipeline services closing cancelled.".
  * Количественное утверждение: **MEASURED** (1 проверка типа `isinstance`).
  * Блокировки отсутствуют.

## 7. `src/bioetl/application/core/preflight/health_aggregator.py`
* **Ревизия (SHA):** `f07ead17df6283b9a7d2d8bfc7e10e2358f97c8b`
* **Метод/команда:** `grep -n -C 20 "CancelledError" src/bioetl/application/core/preflight/health_aggregator.py`
* **Результат:**
  * В методе `check_all` перебираются результаты от `asyncio.gather(..., return_exceptions=True)`.
  * Проверяется `if isinstance(result, asyncio.CancelledError):` и если да, исключение немедленно пробрасывается (`raise result`). Это препятствует агрегации отмененных задач как нездоровых (UNHEALTHY).
  * Количественное утверждение: **MEASURED** (1 проверка типа `isinstance`).
  * Блокировки отсутствуют.

## 8. `src/bioetl/application/core/lifecycle/heartbeat.py`
* **Ревизия (SHA):** `f07ead17df6283b9a7d2d8bfc7e10e2358f97c8b`
* **Метод/команда:** `grep -n -C 20 "CancelledError" src/bioetl/application/core/lifecycle/heartbeat.py`
* **Результат:**
  * В методе `stop` используется `contextlib.suppress(asyncio.CancelledError, PipelineShutdownError):` вокруг `await self._task`.
  * Ожидается, что при вызове `cancel()` для задачи, она может завершиться с `CancelledError`. Это исключение подавляется, чтобы метод `stop` завершился корректно.
  * Количественное утверждение: **MEASURED** (1 использование `contextlib.suppress`).
  * Блокировки отсутствуют.

## 9. `src/bioetl/application/core/lifecycle/lock_lifecycle.py`
* **Ревизия (SHA):** `f07ead17df6283b9a7d2d8bfc7e10e2358f97c8b`
* **Метод/команда:** `grep -n -C 20 "CancelledError" src/bioetl/application/core/lifecycle/lock_lifecycle.py`
* **Результат:**
  * В методе `release_lock` есть блок обработки `except asyncio.CancelledError:`.
  * При возникновении отмены запускается цикл `while not operation.done():`.
  * Внутри цикла сбрасывается флаг отмены задачи (`_clear_task_cancellation()`), и задача `operation` (занимающаяся очисткой блокировки) снова оборачивается в `asyncio.shield`.
  * Вложенный блок `except asyncio.CancelledError:` содержит `continue` (также есть комментарий `# NOSONAR python:S7497 - re-raised below`).
  * После завершения очистки (окончания цикла), оригинальное исключение `CancelledError` поднимается снова (`raise`).
  * Это гарантирует, что блокировка будет обязательно освобождена даже при множественных запросах на отмену задачи.
  * Количественное утверждение: **MEASURED** (2 обработчика `except asyncio.CancelledError:`).
  * Блокировки отсутствуют.
