# Паспорт гигиены репозитория SatoryKono/BioactivityDataAcquisition

## 1. Мёртвый код (Dead Code)
- Устранён мёртвый код: `scripts/engineering/ci/validate_contract_registry.py:346: unreachable code after 'try'`
- Остальные кандидаты (неиспользуемые импорты и переменные, вызванные спецификой тестирования или полиморфизмом) вынесены в `.vulture_whitelist.py` с обоснованием.
- `vulture` прогоняется на src и scripts (confidence 80) без нерешённых находок, `test_dead_code_vulture` проходит.

## 2. Неиспользуемые импорты и недостижимые ветки
- Удалена недостижимая ветка (`return 0`) в `validate_contract_registry.py`.

## 3. Дублирование кода (Duplicate Code)
- `pylint duplicate-code` показал дубли между несколькими модулями в `bioetl.composition.*` и `memory.*`.
- **Доказательство**: анализ дублей показал, что это идентичные списки передаваемых аргументов (kwargs), например `pipeline_config=pipeline_config, logger=logger, ...` или одинаковые имена переменных в тестах/генераторах.
- **Остаточный список на решение владельца**: дубли в `src/memory/` и `bioetl.composition.factories` признаны структурно необходимыми (параметры функций, совпадающие имена ключей конфигурации) и оставлены без изменений, чтобы избежать опасного объединения независимых фабрик, меняющего поведение.

## 4. Прагмы (Type Ignores & Noqa)
- В `src/bioetl` обоснованы и заменены на точечные комментарии все 17 нерешённых `type: ignore` (ранее отмеченных как `tracked(#12721): unjustified type ignore debt`).
- Указаны специфичные технические причины (`technical-reason: ...`) вместо общей заглушки "unjustified type ignore debt".

## 5. Устаревшие TODO/FIXME/XXX
- **Остаточный список на решение владельца**:
  - `scripts/generate_adr_registry.py:        # Find all ADR files (ADR-XXX-*.md pattern)` (паттерн, не долг)
  - `scripts/diagrams/validate_mermaid_syntax.sh:  out_cfg="$(mktemp "${TMPDIR:-/tmp}/puppeteer-validate.XXXXXX.json")"` (паттерн)
  - `scripts/diagrams/lint/lint_diagrams.py:PLACEHOLDER_MARKERS = ["placeholder", "TODO", "FIXME", "stub"]` (константа)
  - `scripts/docs/fixers/sentence_audit.py:                "1) Для каждого пункта ниже либо исправь формулировку, либо укажи TODO на реализацию в коде.\n"` (документация)
  - Вспомогательные shell-скрипты, использующие mktemp с паттерном XXXXXX.
  - Живых TODO/FIXME в `src` не найдено, присутствуют только маски "XXXXXX" и строки для генерации.

## 6. Файловая гигиена
- Корневой набор соответствует `.github/root-allowlist.txt`.
- Мусор и служебные файлы (побочные результаты разовых прогонов) в дереве не найдены.

## 7. Устаревшие скрипты и конфиги
- Неиспользуемых конфигов не обнаружено.

## Дельты метрик
- **Dead code**: -1 мертвая ветка (unreachable).
- **Pragmas**: 17 прагм `tracked(#12721)` заменены на обоснованные `technical-reason`.
- **Duplication**: Без изменений поведения, дубли - структурные сигнатуры вызова.
