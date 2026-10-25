# F-09: проверенная часть conformance-матрицы и границы аудита

## Ревизия и воспроизводимость

Повторная проверка: 2026-10-26, ревизия
`61681a841173d7790b04627bc894db2a0825e9cf`, Python 3.13.7, Windows.
Исторический отчёт Jules ссылался на `f07ead17df6283b9a7d2d8bfc7e10e2358f97c8b`
и `python generate_report.py`, но этот скрипт и исходный вывод не сохранены.
Поэтому прежние числа 93 порта, 25 реализованных портов и около 33
«непокрытых production bindings» отозваны как **NOT_VERIFIABLE**.

Это **частичная source-bound матрица**, не полный census production bindings.
Полнота F-09 остаётся **BLOCKED / NOT_VERIFIABLE**, а не доказанным отсутствием
поведенческих тестов. Production-код и наборы тестов не изменялись.

## Раздельные критерии

- Signature conformance: присутствие пары в `PORT_ADAPTER_CASES` и проверка
  сигнатур в `tests/architecture/test_adapter_port_conformance.py`.
  Дополнительные два теста этого модуля проверяют runtime-checkable протоколы.
- Production binding: конкретное создание в composition, включая создание
  внутри `StorageBundle`, вложенных объектов и вспомогательных фабрик.
  Одного наследования или нахождения в signature-наборе недостаточно.
- Behavioral coverage: отдельные тесты семантики порта. Отсутствие пары в
  `PORT_ADAPTER_CASES` не означает отсутствие таких тестов.
- Базовые классы `BaseHttpAdapter` и `BaseSyncAdapter` исключены из
  production-числителя: самостоятельное создание в composition не подтверждено.
  Из этого не выводится отсутствие production bindings у конкретных подклассов.

## Проверенные пары

Пути в таблице заданы относительно `src/bioetl/`. «Есть» означает наличие
пары в signature-наборе, а не полную проверку поведения.

| Concrete adapter → port | Свидетельство production binding | Signature-набор |
|---|---|---|
| `BronzeWriter → BronzeStoragePort` | `composition/bootstrap/assembly/storage.py`, `bootstrap_storage_adapter`: `StorageBundle(bronze_writer=BronzeWriter(...))`; фабричный путь через `composition/factories/storage/factory.py` и `_bronze.py` | Есть |
| `SilverWriter → SilverStoragePort` | тот же `bootstrap_storage_adapter`: `silver_writer=SilverWriter(...)`; фабричный путь через `factory.py`, `_layer_writers.py` и `_silver.py` | Есть |
| `GoldWriter → GoldStoragePort` | тот же `bootstrap_storage_adapter`: `gold_writer=GoldWriter(...)`; фабричный путь через `factory.py`, `_layer_writers.py` и `_gold.py` | Есть |
| `NoOpLogger → LoggerPort` | `composition/bootstrap/cli/noop.py`, `create_noop_logger`: `NoOpLogger()` | Есть |
| `UnifiedLogger → LoggerPort` | `composition/bootstrap/runtime/logger_bootstrap.py`, `_default_logger_factory`: возвращает `UnifiedLogger(...)` как `LoggerPort` | Есть |
| `StructlogLogger → LoggerPort` | создание в `infrastructure/observability/logging.py::create_logger` подтверждено; вызов этой фабрики из composition **не подтверждён**, production binding в итог ниже не включён | Есть |
| `CircuitBreakerGuard → CircuitBreakerPort` | `composition/factories/datasource/http_client.py`: создание внутри HTTP-клиента; также `composition/factories/datasource/pubchem.py` | Есть |
| `MemoryLock → LockPort` | `composition/factories/services/port_factories.py::create_lock`: создаёт `MemoryLock()`, проверяет `isinstance(lock, LockPort)`, возвращает `LockPort` | Нет; это только пробел данного signature-набора |

## Пересчитанные показатели ограниченной выборки

- **7** явных пар в `PORT_ADAPTER_CASES`, **5** различных портов.
- В таблице **8** различных пар: эти 7 плюс `MemoryLock → LockPort`.
- Для **7 из этих 8** пар здесь приведено создание в composition,
  соответствующее **6** различным портам. Это не число по всему репозиторию.
- Из этих 7 подтверждённых production-пар **6** есть в signature-наборе,
  **1** (`MemoryLock`) отсутствует именно в нём.
- `StructlogLogger` учтён в signature-наборе, но не прибавлен к
  подтверждённым production-парам. Базовые классы не учтены.
- Общее число production-пар и их behavioral-покрытие **не установлены**;
  проценты полноты по всему репозиторию не вычисляются.

## Поведенческие контракты MemoryLock

Покрытие существует вне signature-набора:

- `tests/architecture/test_port_contracts_hypothesis.py::TestLockPortProperties`:
  `test_acquire_release_cycle_is_consistent`, `test_heartbeat_extends_ttl`,
  `test_multiple_locks_are_independent`.
- `tests/architecture/test_port_contracts_resilience_concurrency.py::TestLockPortErrorConditions`:
  проверки release и heartbeat с неверным владельцем и несуществующего ключа.

Команда из `C:/BioactivityDataAcquisition/pr12536`:

```text
C:/BioactivityDataAcquisition/work/.venv-win/Scripts/python.exe -m pytest tests/architecture/test_adapter_port_conformance.py tests/architecture/test_port_contracts_hypothesis.py tests/architecture/test_port_contracts_resilience_concurrency.py -k "infrastructure_adapter or runtime_checkable or LockPort" -q --no-cov
```

Результат: exit **0**, **20 выбранных тестов прошли**. Остальные тесты этих
модулей не запускались этой командой. Это локальное свидетельство выбранных
контрактов, не полная behavioral-матрица и не независимая приёмка F-09.

## Оставшаяся работа F-09

Для полного аудита нужен воспроизводимый census с трассировкой каждой пары
к реальному composition binding и отдельно к signature/behavioral тестам.
Историческая таблица наследования не удовлетворяет этому критерию и не
используется как список доказанных production-пробелов.
Независимый проверяющий не назначен; формальное закрытие F-09 не заявляется.
