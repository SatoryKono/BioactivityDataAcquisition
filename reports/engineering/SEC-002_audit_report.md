# Аудит-отчёт: SEC-002

## Объект проверки
Использование `defusedxml` в пути парсинга PubMed XML, лимиты ресурсов, снятие nosec B405 (согласно Issue #12470).

## Версии окружения
- Ревизия: `c08883508249e87d297f3b306e7a4d032e36de02`
- Исторически заявлены Python `3.13.14` и Expat `expat_2.8.1`; исходный вывод не сохранён, поэтому эти версии **NOT_VERIFIABLE**, не MEASURED.

### Воспроизводимая повторная проверка 2026-10-26

- Проверяемая ревизия: `2ac954f9c1e85f261a3c3ab19e920e980680a4fa`.
- Рабочий каталог: `C:/BioactivityDataAcquisition/pr12491`.
- Команда: `C:/BioactivityDataAcquisition/work/.venv-win/Scripts/python.exe -m pytest tests/security/test_pubmed_xxe_mitigation.py -q --no-cov`.
- Результат: exit `0`, все **3 теста прошли** (`... [100%]`). Это подтверждает только существующие XXE/entity-expansion сценарии, не лимиты ресурсов и не весь SEC-002.
- Команда окружения: `C:/BioactivityDataAcquisition/work/.venv-win/Scripts/python.exe -c "import sys,pyexpat; print(sys.version); print(pyexpat.EXPAT_VERSION)"`.
- Результат: exit `0`, Python `3.13.7`, Windows MSC v.1944 64 bit (AMD64), `expat_2.7.1`.
- Bandit повторно **не запускался**. Команда, версия и результат исторического запуска отсутствуют: **NOT_VERIFIABLE**. Наличие подавлений ниже — наблюдение исходного кода, а не свидетельство запуска Bandit.

## Результаты проверок

### 1. Парсинг XML PubMed внешнего ввода (defusedxml)
- `src/bioetl/infrastructure/adapters/pubmed/xml_processor.py`, метод `PubMedXmlProcessor.parse_response`: парсинг `xml_text` использует `defused_ET.fromstring(xml_text)`.
- Тот же метод корректно перехватывает и обрабатывает исключение `defused_ET.EntitiesForbidden`.
- Обычный `xml.etree.ElementTree` импортируется как `ET`, но используется только для аннотаций типов (`ET.Element`) и для `ET.tostring` (сериализация, не парсинг).
- Ожидаемый результат: Внешний ввод парсится безопасным `defusedxml`. ПРОВЕРЕНО (PASS).

### 2. Лимиты ресурсов defusedxml (Размер, Время, Память)
- В `xml_processor.py` (или где-либо ещё) **ОТСУТСТВУЮТ** явные проверки/ограничения на размер XML (`len(xml_text)`), время выполнения парсинга или потребление памяти.
- `defusedxml` защищает от миллиарда смешков (entity expansion) и загрузки внешних сущностей, но **не ограничивает** потребление ресурсов при парсинге огромных файлов (например, файлов размером в гигабайты, состоящих из глубоко вложенных легальных тегов) (quadratic blowup / resource exhaustion).
- Ожидаемый результат: Наличие лимитов размера/времени/памяти перед парсингом. ПРОВЕРЕНО (BLOCKER).

### 3. Снятие nosec B405 в путях парсинга
- Найдено множество импортов `xml.etree.ElementTree` с подавлением `# nosec B405 - see suppression registry`:
  - `src/bioetl/infrastructure/adapters/pubmed/xml_processor.py:16`
  - `src/bioetl/application/pipelines/pubmed/xml_parser.py:11`
  - `src/bioetl/application/pipelines/pubmed/_block_helpers.py:6`
  - и другие (extractors, block definitions, transformer).
- Подавления видны в исходном коде; подтверждение фактическим запуском `bandit` отсутствует (**NOT_VERIFIABLE**). Код не очищен от `nosec B405` для этих файлов (хотя многие используют `ET` лишь для типов).
- Ожидаемый результат: "bandit чист без подавлений на parsing-путях". ПРОВЕРЕНО (BLOCKER).

### 4. Тесты (entity expansion, quadratic blowup, oversized)
- В `tests/security/test_pubmed_xxe_mitigation.py` есть тесты `test_transformer_xxe_mitigation`, `test_xml_processor_xxe_mitigation` и `test_transformer_billion_laughs_mitigation`. Они проходят (PASS) в повторной проверке на ревизии и окружении, указанных выше; исторический запуск отдельно не подтверждён.
- Тестов на "oversized" (очень большие XML-документы) или лимиты времени/памяти **нет**.
- Ожидаемый результат: Вредоносные XML-фикстуры (entity expansion, quadratic blowup, oversized) отклоняются контролируемо. ПРОВЕРЕНО (BLOCKER).

## Вывод
Проверка выявила несоответствия критериям готовности (отсутствие лимитов размера/времени, наличие `nosec B405` в parsing-путях, отсутствие тестов на oversized).
В соответствии с инструкциями (read-only audit, Mode=READ_ONLY), эти несоответствия фиксируются как явный **BLOCKER**. Кодовые мутации не производятся.
