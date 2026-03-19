# RF-FS-007 Baseline Plan

**Дата:** 2026-03-19  
**Тема:** Формализовать контракт структуры adapter packages и убрать случайную асимметрию между провайдерами  
**Связанные находки:** `FS-010`, частично `FS-011`  
**Основной scope:** `src/bioetl/infrastructure/adapters/`, `tests/architecture/test_adapter_contracts.py`, а также активная архитектурная документация, если потребуется зафиксировать правила

## Цель

`RF-FS-007` должен закрепить ответ на простой, но пока недостаточно формализованный вопрос: как должна выглядеть корректная файловая структура provider adapter package в BioETL. На текущем baseline в `src/bioetl/infrastructure/adapters/` уже видна сильная асимметрия. Условно “лёгкие” пакеты имеют только `client.py`, у некоторых есть `exceptions.py`, а более зрелые пакеты вроде UniProt разрослись до множества helper, model и support-модулей. Сама по себе такая асимметрия не всегда является проблемой. Проблема начинается в тот момент, когда структура перестаёт что-либо объяснять: нельзя понять, какие файлы являются обязательными для каждого provider package, какие считаются нормальным extension surface, а какие являются историческим налётом.

Цель этого RF не в том, чтобы искусственно сделать все adapter packages одинаковыми. Это было бы архитектурно неверно и повредило бы практической эволюции пакетов. Правильная цель — определить минимальный контракт структуры, различить обязательные и опциональные элементы, а затем выровнять явные отклонения только там, где они реально мешают навигации, тестам и architecture governance.

## Базовый диагноз

На текущем состоянии проекта package-level contract у адаптеров существует скорее неформально. Аудит уже показал, что:
- `chembl` выглядит очень минималистично;
- `crossref` содержит `client.py` и `exceptions.py`;
- `semanticscholar` уже имеет более развитую локальную структуру;
- `uniprot` заметно шире и содержит около двух десятков `.py` файлов.

Отсюда следует важный вывод: нельзя требовать строгой симметрии вида `client.py + transformer.py + exceptions.py` для каждого provider package. Это прямо конфликтует с архитектурными правилами проекта, потому что transformers относятся к `application`, а не к `infrastructure`. Следовательно, контракт должен быть построен не на ложной симметрии, а на роли адаптера в Hexagonal Architecture.

## Архитектурный принцип

Внутри `infrastructure/adapters/{provider}/` должны жить только infrastructure-facing concerns:
- HTTP/API client behavior;
- provider-specific transport/request helpers;
- response parsing helpers, если они инфраструктурны по смыслу;
- transport/runtime exceptions;
- health/retry adjuncts;
- provider-local DTO или response models, если они не являются доменными объектами.

Там не должны появляться:
- application transformers;
- composition factories;
- доменные aggregate/value-object implementation details;
- случайные shared utility modules, которые на деле нужны нескольким провайдерам.

Именно этот принцип нужно положить в основу `RF-FS-007`.

## Целевая модель package contract

Для provider adapter package стоит зафиксировать трёхуровневую модель.

### 1. Обязательный минимум

Каждый provider package должен иметь один явный entrypoint для adapter/client surface. В большинстве случаев это `client.py`. Если в пакете исторически уже есть sanctioned root import через `client.py`, сохранять его стоит как canonical public seam.

### 2. Опциональные стандартные расширения

Следующие модули допустимы, но не обязательны:
- `exceptions.py`
- response/request `models.py`
- `_helpers.py` или узкие helper-модули с честными именами
- health/retry/pagination support modules
- provider-local parsing modules

Ключевое правило здесь в том, что имя должно отражать реальную роль. Вводить vague-файлы вида `utils.py` или `common.py` без жёсткой причины нельзя.

### 3. Growth paths

Если provider package перерастает один-два файла, это нормально, но рост должен быть объяснимым. Например:
- отдельный подпакет для extractors/parsers;
- отдельный модуль под retry/pagination behavior;
- отдельные response model modules.

Но такой рост должен происходить по устойчивым темам, а не добавлением случайных helper-файлов на один уровень.

## Что конкретно нужно сделать

### Шаг 1. Зафиксировать contract

Сначала нужно явно определить, что считается корректной структурой adapter package. Это можно сделать через:
- обновление `tests/architecture/test_adapter_contracts.py`;
- при необходимости короткий governance/reference doc;
- возможно, через лёгкий manifest-стиль список допустимых package forms.

Без этого любая “нормализация” останется вкусовщиной.

### Шаг 2. Разделить mandatory и optional

Нужно формально закрепить:
- `client.py` как canonical minimum entrypoint;
- `exceptions.py` как optional, но preferred when transport-specific errors exist;
- helper/model/parser modules как optional extensions;
- отсутствие требования к `transformer.py`.

Это самый важный архитектурный момент всей задачи.

### Шаг 3. Проверить существующие provider packages

После определения контракта нужно пройтись по реальным пакетам:
- `chembl`
- `crossref`
- `openalex`
- `pubchem`
- `pubmed`
- `semanticscholar`
- `uniprot`

Задача не в том, чтобы всех привести к одной форме, а в том, чтобы выявить реальные отклонения:
- неясный entrypoint;
- модули с misleading names;
- helper files, которые должны быть shared и жить вне provider package;
- пакеты, где публичный surface размазан между несколькими файлами без причины.

### Шаг 4. Решить adjacent single-file namespace cases

Хотя single-file namespaces формально относятся к соседней находке, часть этой логики примыкает к adapter governance. Если вокруг адаптеров существуют namespace-пакеты с одним модулем и без package-level смысла, их стоит пересмотреть отдельно. Но это не должно затмить сам provider contract. Эта часть является вторичной.

## Риски

Риск этой задачи низкий или ближе к среднему, но есть три важных ловушки. Первая — навязать псевдосимметрию и тем самым сломать архитектурный смысл слоёв. Вторая — превратить contract в чрезмерно жёсткий lint, который будет мешать естественному росту более сложных адаптеров вроде UniProt. Третья — сделать contract слишком общим, после чего `test_adapter_contracts.py` останется формальной проверкой, не дающей реального governance эффекта.

## Минимизация рисков

- Строить contract вокруг роли пакета в архитектуре, а не вокруг внешней симметрии.
- Явно прописать, что `transformer.py` не является частью adapter contract.
- Разрешить optional growth patterns для более сложных провайдеров.
- Проверять существующие пакеты на meaningful deviations, а не на непохожесть друг на друга.

## Верификация

Базовый verify-set для этой задачи должен быть лёгким, потому что RF mostly governance/structure-oriented:

```bash
./.venv/Scripts/python.exe -m pytest tests/architecture/test_adapter_contracts.py -q
```

Параллельно:

```bash
./.venv/Scripts/python.exe scripts/docs/check_doc_links.py --configs
```

Если в ходе выравнивания будут меняться импорты или package layout:

```bash
./.venv/Scripts/python.exe -m pytest tests/architecture/test_forbidden_imports.py tests/architecture/test_layer_dependencies.py -q
./.venv/Scripts/python.exe -m mypy --strict --no-incremental src/bioetl/
```

При адресных изменениях конкретного провайдера дополнительно нужны его unit suites.

## Definition of Done

`RF-FS-007` можно считать завершённым, если:
- существует явный и краткий adapter package contract;
- `test_adapter_contracts.py` проверяет реальное правило, а не декоративную симметрию;
- для новых provider packages понятно, какой минимум обязателен и какие расширения допустимы;
- packages не обязаны содержать application-level artifacts;
- явные misleading structures либо исправлены, либо documented as intentional.

Итоговая цель этого RF — сделать структуру adapter packages предсказуемой и архитектурно честной, не жертвуя гибкостью там, где провайдеры действительно различаются по сложности.
