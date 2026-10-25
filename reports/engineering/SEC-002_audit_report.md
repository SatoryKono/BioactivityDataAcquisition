# Аудит-отчёт: SEC-002

## Объект проверки
Использование `defusedxml` в пути парсинга PubMed XML, лимиты ресурсов, снятие nosec B405 (согласно Issue #12470).

## Версии окружения
- Ревизия: `c08883508249e87d297f3b306e7a4d032e36de02`
- Python: `3.13.14`
- Expat (`pyexpat.EXPAT_VERSION`): `expat_2.8.1` (MEASURED)

## Результаты проверок

### 1. Парсинг XML PubMed внешнего ввода (defusedxml)
- `src/bioetl/infrastructure/adapters/pubmed/xml_processor.py`: Парсинг `xml_text` использует `defused_ET.fromstring(xml_text)` (строка 33).
- Исключение `defused_ET.EntitiesForbidden` корректно перехватывается и обрабатывается (строки 35-39).
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
- Запуск `bandit` подтверждает, что эти подавления остаются в коде, и `bandit` их игнорирует. Код не очищен от `nosec B405` для этих файлов (хотя многие используют `ET` лишь для типов).
- Ожидаемый результат: "bandit чист без подавлений на parsing-путях". ПРОВЕРЕНО (BLOCKER).

### 4. Тесты (entity expansion, quadratic blowup, oversized)
- В `tests/security/test_pubmed_xxe_mitigation.py` есть тесты `test_transformer_xxe_mitigation`, `test_xml_processor_xxe_mitigation` и `test_transformer_billion_laughs_mitigation`. Они проходят (PASS).
- Тестов на "oversized" (очень большие XML-документы) или лимиты времени/памяти **нет**.
- Ожидаемый результат: Вредоносные XML-фикстуры (entity expansion, quadratic blowup, oversized) отклоняются контролируемо. ПРОВЕРЕНО (BLOCKER).

## Вывод
Проверка выявила несоответствия критериям готовности (отсутствие лимитов размера/времени, наличие `nosec B405` в parsing-путях, отсутствие тестов на oversized).
В соответствии с инструкциями (read-only audit, Mode=READ_ONLY), эти несоответствия фиксируются как явный **BLOCKER**. Кодовые мутации не производятся.
