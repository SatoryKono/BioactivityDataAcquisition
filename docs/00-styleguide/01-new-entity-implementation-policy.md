# Политика создания и локализации новых объектов (ABC / Default / Impl и т.д.)

## Purpose and scope

**Цель.** Установить однозначные правила именования, размещения, регистрации и поддержки абстракций (ABC / Protocol), их дефолтных фабрик (Default) и конкретных реализаций (Impl).
**Область применения.** Политика применяется ко всему коду в `src/bioetl/clients` и сопутствующим реестрам, документации и CI-конфигурации.

## Sources of truth

* `src/bioetl/clients/base/contracts.py` — shared Protocol / ABC (source of truth для общих контрактов).
* `src/bioetl/clients/<domain>/contracts.py` — domain-scoped contracts.
* `src/bioetl/clients/<domain>/factories.py` — Default factories (рекомендуемая локализация).
* `src/bioetl/clients/<domain>/impl/` — реализационные модули (Impl).
* `src/bioetl/clients/base/abc_registry.yaml` — машинный реестр ABC (source of truth).
* `src/bioetl/clients/base/abc_impls.yaml` — мэппинг Default / Impl (source of truth).
* `docs/01-ABC/INDEX.md` — человекочитаемый каталог ABC (source of truth для людей).
* CI configuration (`.github/workflows/*`) — правила проверки и исполнения политики.

---

## Quick cheat-sheet (1 page)

* **Новый ABC?** Создать Default (может быть stub), обновить `abc_registry.yaml`, `docs/01-ABC/INDEX.md`, и добавить Default в `abc_impls.yaml`.
* **Новый Impl?** Разместить в `impl/`, добавить запись в `abc_impls.yaml`, добавить тесты и документацию. Не требуется новый Default.
* **Нейминг:** Классы PascalCase; функции snake_case; файлы snake_case.py. Суффиксы: `Factory`, `ClientFactory`, `DataClient`, `Client`, `Facade`, `Registry`, `Adapter`, `Transport`, `Protocol`/`ABC`, `Config`/`Model`/`Params`, `Error`.
* **Докстринг ABC:** Обязательный структурированный блок (см. раздел «Докстринг у ABC»). CI проверяет его наличие.
* **CI:** Регекс-проверки нейминга, проверка наличия Default при создании ABC, синхронизация реестров, проверка докстринга, соответствие имен классов и файлов.

---

## Enforcement and exceptions  <!-- таблица: кто, как, когда -->

| #таблицы-01.01 | Rule / Subject      | Responsible                             | Exception process                                                                                                             | Актуальность | Description                                                                                       |
| -------------: | ------------------- | --------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- | :----------: | ------------------------------------------------------------------------------------------------- |
|          01.01 | Enforcement Owner   | Architecture team (or designated owner) | Exceptions require documented PR, approval by architecture owner, and a time-limited waiver recorded in `configs/naming_exceptions.yaml`. |     true     | Архитектурная команда отвечает за исполнение политики, рассмотрение исключений и соответствие CI. |
|          01.02 | Exception Recording | PR author & approver                    | Все исключения документируются с rationale, expiry date и reviewer в `configs/naming_exceptions.yaml` и привязываются к PR.               |     true     | Исключения не допускаются устно.                                                                  |
|          01.03 | Audit & Revocation  | Security/Architecture                   | Периодический аудит (quarterly). Стаpые исключения отзываются; нарушения требуют remediation план.                            |     true     | Аудит фиксируется и доводится до владельцев.                                                      |

**Единый источник исключений:** `configs/naming_exceptions.yaml`. Для любых отступлений используйте только эту YAML-структуру; отдельного `docs/exceptions.md` не требуется.

---

## 1. Общие правила именования (таблица правил)

**Контекст.** Используйте эти правила для написания кода и для CI-регекс-проверок. Примеры оформлены в `code`-стиле.

| #таблицы-02.01 | Rule                               |                Pattern / Example | Актуальность | Description                             |
| -------------: | ---------------------------------- | -------------------------------: | :----------: | --------------------------------------- |
|          02.01 | Class names must be PascalCase     |               `ChemblDataClient` |     true     | Имена классов в PascalCase.             |
|          02.02 | Functions/methods in snake_case    |        `fetch_one`, `iter_pages` |     true     | Функции и методы — snake_case.          |
|          02.03 | Filenames in snake_case.py         |                 `data_client.py` |     true     | Файлы — snake_case.py.                  |
|          02.04 | Private names start with `_`       |           `_resilient_transport` |     true     | Приватные сущности — с `_`.             |
|          02.05 | Export public symbols in `__all__` | `__all__ = ["ChemblDataClient"]` |     true     | Публичные сущности явно экспортируются. |

*(CI: регулярные выражения проверяют соответствие этим правилам.)*

---

## 2. Роли классов — однозначные суффиксы (таблица)

**Контекст.** Суффиксы должны позволять понять роль класса по имени.

| #таблицы-03.01 | Role                       |               Required Suffix | Актуальность | Description                           |
| -------------: | -------------------------- | ----------------------------: | -----------: | ------------------------------------- |
|          03.01 | Factory (general)          |                     `Factory` |         true | Фабрики — `Factory`.                  |
|          03.02 | ClientFactory              |               `ClientFactory` |         true | Фабрики клиентов — `ClientFactory`.   |
|          03.03 | DataClient (contract impl) |                  `DataClient` |         true | Реализации контрактов — `DataClient`. |
|          03.04 | Client                     |                      `Client` |         true | Общие клиенты — `Client`.             |
|          03.05 | Facade                     |                      `Facade` |         true | Фасады верхнего уровня — `Facade`.    |
|          03.06 | Registry                   |                    `Registry` |         true | Реестры — `Registry`.                 |
|          03.07 | Adapter / Transport        |       `Adapter` / `Transport` |         true | Низкоуровневые адаптеры/транспорты.   |
|          03.08 | Protocol / ABC             |            `Protocol` / `ABC` |         true | Контракты — `Protocol`/`ABC`.         |
|          03.09 | Config / Model / Params    | `Config` / `Model` / `Params` |         true | Конфигурационные/модельные типы.      |
|          03.10 | Error                      |                       `Error` |         true | Исключения — `Error`.                 |

---

## 3. Префиксы функций и смысл (таблица)

**Контекст.** Префиксы отражают стоимость/семантику вызова.

| #таблицы-04.01 | Prefix                          |                        When to use | Актуальность | Description                           |
| -------------: | ------------------------------- | ---------------------------------: | :----------: | ------------------------------------- |
|          04.01 | `get_`                          | Cheap/local reads or cached values |     true     | Для дешёвых операций без сетевого IO. |
|          04.02 | `fetch_`                        |              Network/IO operations |     true     | Для сетевых/дорогих операций.         |
|          04.03 | `iter_`                         |     Return lazy generator/iterator |     true     | Для ленивых итераторов (не `list`).   |
|          04.04 | `create_/build_/make_/default_` |            Object/factory creation |     true     | Для создания объектов/конфигураций.   |
|          04.05 | `register_`                     |               Registration actions |     true     | Для регистрации в реестрах.           |
|          04.06 | `resolve_/ensure_`              |                      Normalization |     true     | Для нормализации/подготовки.          |
|          04.07 | `validate_/parse_/serialize_`   |                 Validation/parsing |     true     | Для валидации/парсинга/сериализации.  |
|          04.08 | `on_`                           |           Event handlers/callbacks |     true     | Для callback/handler функций.         |
|          04.09 | `is_/has_/can_`                 |                     Boolean checks |     true     | Для булевых проверок.                 |

---

## 4. Правила свойств и параметров (таблица)

| #таблицы-05.01 | Rule                                       |           Pattern / Example | Актуальность | Description                           |
| -------------: | ------------------------------------------ | --------------------------: | :----------: | ------------------------------------- |
|          05.01 | Public properties as nouns                 |            `name`, `source` |     true     | Публичные свойства — существительные. |
|          05.02 | Private properties with leading underscore |   `_delegate`, `_transport` |     true     | Приватные — с `_`.                    |
|          05.03 | Boolean flags in positive form             | `is_enabled`, `allow_cache` |     true     | Булевы имена в позитивной форме.      |
|          05.04 | Config/options names                       |         `config`, `options` |     true     | Использовать полные слова для опций.  |
|          05.05 | Collections in plural                      |       `records`, `adapters` |     true     | Коллекции — во множественном числе.   |

---

## 5. Правила для файлов и пакетов (таблица)

| #таблицы-06.01 | Artifact                |                            Filename / Path | Актуальность | Description                                            |
| -------------: | ----------------------- | -----------------------------------------: | :----------: | ------------------------------------------------------ |
|          06.01 | Shared contracts        |     `src/bioetl/clients/base/contracts.py` |     true     | Общие протоколы и типы в одном месте.                  |
|          06.02 | Domain contracts        | `src/bioetl/clients/<domain>/contracts.py` |     true     | Домен-специфичные контракты рядом с реализациями.      |
|          06.03 | Default factories       | `src/bioetl/clients/<domain>/factories.py` |     true     | Default фабрики в `factories.py`.                      |
|          06.04 | Impl directory          |        `src/bioetl/clients/<domain>/impl/` |     true     | Конкретные реализации в `impl/`.                       |
|          06.05 | Transport/adapter files |             `transport.py`, `*_adapter.py` |     true     | Низкоуровневые транспорты/адаптеры в отдельных файлах. |
|          06.06 | Registry files          |                              `registry.py` |     true     | Реестры в `registry.py`.                               |

---

## 6. Политика создания новых ABC / Protocol (процесс и правила)

**Краткий процесс при создании нового ABC / Protocol:**

1. Добавить ABC / Protocol в `src/bioetl/clients/<domain>/contracts.py` (или в `base/contracts.py` если shared).
2. В докстринге ABC добавить обязательный структурированный блок (см. раздел «Докстринг у ABC»).
3. Создать Default factory в `src/bioetl/clients/<domain>/factories.py` (может быть stub с `NotImplementedError`).
4. Обновить `abc_impls.yaml` → добавить `default` для нового ABC.
5. Обновить `abc_registry.yaml` и `docs/01-ABC/INDEX.md`.
6. Добавить PR-тесты/юнит-тесты и следовать PR-чеклисту.

**Таблица правил и процесса**

| #таблицы-07.01 | Rule                                     | Актуальность | Description                                                                                           |
| -------------: | ---------------------------------------- | :----------: | ----------------------------------------------------------------------------------------------------- |
|          07.01 | Default mandatory on ABC creation        |     true     | При создании ABC обязательно добавить Default factory (даже stub).                                    |
|          07.02 | Default may be a stub if no Impl exists  |     true     | Если реальных имплементаций нет, Default может бросать `NotImplementedError` или возвращать заглушку. |
|          07.03 | Adding Impl does not require new Default |     true     | Появление имплементации не обязывает создание нового Default.                                         |
|          07.04 | ABC docstring mandatory structured block |     true     | ABC обязаны иметь структурированный докстринг (см. отдельный раздел).                                 |

---

## 7. Default и Impl — детальные требования

**Контекст.** Default — рекомендуемая точка входа; Impl — конкретная реализация. CI и реестры опираются на `abc_impls.yaml`.

| #таблицы-08.01 | Artifact               |                        Placement / Pattern | Актуальность | Description                                                           |
| -------------: | ---------------------- | -----------------------------------------: | :----------: | --------------------------------------------------------------------- |
|          08.01 | Default factory naming |                `default_<domain>_<entity>` |     true     | Имя дефолтной фабрики с префиксом `default_`.                         |
|          08.02 | Default placement      | `src/bioetl/clients/<domain>/factories.py` |     true     | Default в `factories.py`.                                             |
|          08.03 | Impl naming            |               `[Domain][Entity][Role]Impl` |     true     | Реализации с суффиксом `Impl` (например, `ChemblDataClientHTTPImpl`). |
|          08.04 | Impl placement         |        `src/bioetl/clients/<domain>/impl/` |     true     | Все имплементации в `impl/`.                                          |
|          08.05 | Registration of Impl   |                    `abc_impls.yaml` update |     true     | Каждая новая имплементация добавляется в `abc_impls.yaml`.            |

**Операционные замечания:**

* Default должен быть единой рекомендуемой точкой входа для потребителя; имплементации регистрируются отдельно.
* `abc_impls.yaml` поддерживает структуру `ABC -> { default: [], impls: [] }`. CI валидирует синхронизацию.

---

## 8. Реестры и форматы

**Контекст.** Машинный и человекочитаемый каталоги — отдельные источники истины.

| #таблицы-09.01 | Artifact          |                                                                                                     Format / Example | Актуальность | Description                              |
| -------------: | ----------------- | -------------------------------------------------------------------------------------------------------------------: | :----------: | ---------------------------------------- |
|          09.01 | abc_registry.yaml | YAML list of ABC objects with name, description, public_interface, file_path, exported_name, default_factory, domain |     true     | Машинный реестр ABC.                     |
|          09.02 | abc_impls.yaml    |                                                                            Mapping ABC -> { default: [], impls: [] } |     true     | Содержит Default и Impl для каждого ABC. |
|          09.03 | docs/01-ABC/INDEX.md |                                                                                Human-readable table with same fields |     true     | Человекочитаемый индекс контрактов.      |

**Практика.** CI проверяет, что: каждый ABC в коде есть в `abc_registry.yaml`; default/impl перечислены в `abc_impls.yaml`; `docs/01-ABC/INDEX.md` отражает реестр.

---

## 9. Докстринг у ABC — формат и проверка

**Контекст.** CI требует присутствие структурированного блока в докстринге ABC. Формат — строгий и машинно-парсимый.
**Обязательные поля (в порядке):**

1. **Краткое описание.** 1–2 предложения, цель и область применения ABC.
2. **Публичный интерфейс.** Список основных public методов с сигнатурами (одна строка на метод, пример: `"fetch_one(self, request: ClientRequest) -> dict"`).
3. **Локализация.** Точный путь к файлу, например: `src/bioetl/clients/base/contracts.py`.
4. **Default/Impl pointers.** Строки-ссылки на рекомендуемый Default factory и на `abc_impls.yaml` (например: `src/bioetl/clients/chembl/factories.py::default_chembl_data_client`).
5. **Примечания/ограничения.** Коротко — допустимые варианты использования и ограничение ответственности.

| #таблицы-10.01 | Field                 |                 Required / Example | Актуальность | Description                                           |
| -------------: | --------------------- | ---------------------------------: | :----------: | ----------------------------------------------------- |
|          10.01 | Краткое описание      |         Required — 1–2 предложения |     true     | Начало докстринга — цель ABC.                         |
|          10.02 | Публичный интерфейс   | Required — methods with signatures |     true     | Перечень публичных методов и сигнатур.                |
|          10.03 | Локализация           |            Required — path to file |     true     | Указать путь к объявлению ABC.                        |
|          10.04 | Default/Impl pointers |        Required — ссылочные строки |     true     | Указать Default factory и ссылку на `abc_impls.yaml`. |

*(CI: парсер проверяет наличие и формат полей.)*

---

## 10. PR-чеклист (пошагово)

**Контекст.** Перед созданием PR автор обязан выполнить пункты ниже.

| #таблицы-11.01 | Item                      |                       Required for | Актуальность | Description                                                           |
| -------------: | ------------------------- | ---------------------------------: | :----------: | --------------------------------------------------------------------- |
|          11.01 | Correct class name & file |             All PRs adding classes |     true     | Имя класса и файл должны соответствовать неймингу и суффиксам.        |
|          11.02 | Default for new ABC       |            PR that creates new ABC |     true     | Новый ABC — с Default (или stub) и записью в `abc_impls.yaml`.        |
|          11.03 | Impl registration         |                     PR adding Impl |     true     | Новая имплементация — запись в `abc_impls.yaml`, тесты, документация. |
|          11.04 | Docs & registry update    | PR adding/modifying ABC or Default |     true     | Обновить `docs/01-ABC/INDEX.md` и `abc_registry.yaml`.                   |
|          11.05 | Tests                     |   All changes that affect behavior |     true     | Unit/integration тесты там, где нужно.                                |

**Набор действий для автора PR (последовательность):**

1. Локально проверить нейминг и формат докстринга.
2. Добавить/обновить Default/Impl и соответствующие файлы.
3. Обновить `abc_impls.yaml` и `abc_registry.yaml`.
4. Обновить `docs/01-ABC/INDEX.md`.
5. Добавить тесты.
6. Убедиться, что CI проходит локально/в PR.

---

## 11. CI / pre-commit checks (таблица)

**Контекст.** CI автоматически проверяет соответствие кода политике.

| #таблицы-12.01 | Check                         |                   What it verifies | Актуальность | Description                                                                 |
| -------------: | ----------------------------- | ---------------------------------: | :----------: | --------------------------------------------------------------------------- |
|          12.01 | Naming regex checks           | Class suffix and function prefixes |     true     | Статическая проверка имён по регексам (см. `naming_checks.py`).             |
|          12.02 | Default existence for new ABC |  `abc_impls.yaml` contains default |     true     | При добавлении ABC проверяется наличие `default` записи.                    |
|          12.03 | abc_registry sync             |   `abc_registry.yaml` содержит ABC |     true     | Проверка, что ABC зарегистрирован.                                          |
|          12.04 | Docstring block presence      |       ABC has structured docstring |     true     | Парсер проверяет обязательные поля в докстринге.                            |
|          12.05 | File/class name match         |            Public class ↔ filename |     true     | Если файл содержит один публичный класс, CI сверяет имя класса и имя файла. |

**Примечание.** Конкретные регекс-настройки и правила находятся в `naming_checks.py` и в CI конфигурации `.github/workflows/*`.

---

## 12. Enforcement and exceptions — подробности

| #таблицы-13.01 | Exception Type              |       Who approves | Validity period |                               How recorded | Актуальность | Description                                                     |
| -------------: | --------------------------- | -----------------: | --------------: | -----------------------------------------: | :----------: | --------------------------------------------------------------- |
|          13.01 | Naming exception            | Architecture owner |   up to 90 days | Record in `configs/naming_exceptions.yaml` + PR note |     true     | Временное отступление по именованию с фиксацией и сроком.       |
|          13.02 | No-default-on-ABC exception | Architecture board |   up to 30 days |    PR rationale and `configs/naming_exceptions.yaml` |     true     | Разрешение не создавать Default для нового ABC при обосновании. |
|          13.03 | Registry-sync delay         |    Repo maintainer |          7 days | Issue linked to PR and `abc_registry.yaml` |     true     | Если реестр не обновлён, создаётся issue с 7-дневным сроком.    |

---

## 13. Examples & templates (short pointers)

* `contracts_template.py` — шаблон Protocol/ABC с требуемым докстринг-блоком.
* `factories_template.py` — шаблон Default factory и описание параметров.
* `impl_http_template.py` — skeletal Impl класс.
* `registry_template.py` — пример доменного реестра.
* `naming_checks.py` — скрипт с регексами и проверкой присутствия Default при создании ABC.

---

## 14. Auditability and change log

* Все изменения в публичных интерфейсах ABC или Default фиксируются в `UPGRADING.md` (дата, автор, причина, migration notes).
* Архитектура проводит квартальные аудиты; результаты и ревоки исключений документируются.

---

## 15. Appendices: Example `abc_registry.yaml` entry (machine-readable)

```yaml
- name: DataClientProtocol
  description: "Контракт для клиентов доступа к данным: fetch_one, iter_pages и др."
  public_interface:
    - "fetch_one(self, request: ClientRequest) -> dict"
    - "iter_pages(self, params: PaginationParams) -> Iterator[Page]"
  file_path: "src/bioetl/clients/base/contracts.py"
  exported_name: "DataClientProtocol"
  default_factory: "src/bioetl/clients/chembl/factories.py::default_chembl_data_client"
  domain: "base"
```

