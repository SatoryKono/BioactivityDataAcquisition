## Цели

* Перевести тесты на единый интерфейс парсера `parse(...)` вместо `parse_response(...)`

* Сохранить зелёные тесты, инварианты детерминизма и нулевую сумму классов

## Охват

* Только тестовые файлы: `tests/**`

* Без изменения прод‑кода; совместимость уже обеспечена алиасами

## Изменения по файлам

* tests/bioetl/infrastructure/clients/chembl/test\_response\_parser.py

  * Заменить вызовы `parser.parse_response(resp)` → `parser.parse(resp)`

* tests/bioetl/application/pipelines/chembl/test\_extraction.py

  * Моки: `mock_parser.parse_response.return_value`/`side_effect` → `mock_parser.parse.return_value`/`side_effect`

  * В проверках: `mock_client.request_builder.build.assert_called_with({...})` оставить без изменений

* tests/bioetl/infrastructure/clients/chembl/test\_fallback\_client.py

  * Класс `DummyParser`: реализовать `parse(...)` (и при желании оставить `parse_response(...)` как делегат)

  * Использования `parse_response` заменить на `parse`

* tests/bioetl/infrastructure/files/test\_csv\_record\_source.py

  * Локальные фейки парсера: заменить методы `parse_response(...)` на `parse(...)`

* tests/bioetl/domain/test\_record\_source.py

  * Тестовый парсер: переименовать метод `parse_response(...)` → `parse(...)`

## Правила и совместимость

* Не добавлять новые классы (нулевая сумма); модифицировать существующие тестовые классы

* Сохранить семантику тестов (объёмы/порядок данных) — только имя метода меняется

* В местах жёсткой проверки цепочки билдера (`build_for_endpoint().build_request({})`) не трогать

## Верификация

* Запустить целевые тесты модулей ChEMBL и источников данных; затем полный `pytest`

* Подтвердить отсутствие регрессий в golden‑тестах (артефакты идентичны)

## Риски и смягчение

* Несоответствие моков: тщательно заменить `return_value`/`side_effect` и ожидания `assert_called`

* Случайные пропуски: прогон `grep` по `parse_response(` в `tests/**` после изменений

## Итог

* Тесты переведены на `parse(...)`, единый интерфейс соблюдён; обратная совместимость прод‑кода сохранена

