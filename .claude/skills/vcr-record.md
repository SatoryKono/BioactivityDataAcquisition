# /vcr-record

Запись и управление VCR-кассетами для HTTP-тестов в BioETL.

## Использование

```
/vcr-record [action] [target]
```

**Действия:**
- `record` — записать новую кассету (по умолчанию)
- `list` — показать существующие кассеты
- `clean` — очистить устаревшие кассеты
- `validate` — проверить кассеты на секреты
- `update` — перезаписать существующую кассету

**Цели:**
- `test_name` — конкретный тест (например: `test_fetch_activities`)
- `provider` — все тесты провайдера (например: `chembl`)
- `file` — все тесты в файле

**Примеры:**
```
/vcr-record test_fetch_activities           # Записать кассету для теста
/vcr-record list chembl                     # Показать кассеты ChEMBL
/vcr-record validate                        # Проверить все на секреты
/vcr-record update test_health_check        # Перезаписать кассету
/vcr-record clean --older-than 90           # Удалить старше 90 дней
```

---

## Инструкции для Claude

### Действие: `record` (по умолчанию)

Записать новую VCR-кассету для теста.

**Шаг 1: Найти тест**
```bash
# Поиск теста по имени
grep -r "def test_target_name" tests/ --include="*.py" -l
```

**Шаг 2: Определить провайдера**
```bash
# Из пути теста определить провайдер
# tests/integration/chembl/ → chembl
# tests/integration/adapters/uniprot/ → uniprot
```

**Шаг 3: Записать кассету**
```bash
cd "E:\g-drive\05_AI\github\BioactivityDataAcquisition2"

# Запустить тест с режимом записи (bash syntax)
VCR_RECORD_MODE=new_episodes uv run pytest tests/path/to/test_file.py::TestClass::test_method -v -s
```

**Шаг 4: Валидация кассеты**
```bash
# Проверить что кассета создана
ls tests/fixtures/vcr/{provider}/

# Проверить на секреты
grep -i "api_key\|apikey\|password\|secret\|token\|email" tests/fixtures/vcr/{provider}/*.yaml
```

**Шаг 5: Санитизация (если нужно)**
Если найдены секреты, отредактировать кассету:
```yaml
# Заменить реальные значения на плейсхолдеры
headers:
  Authorization: "Bearer REDACTED"
  X-Api-Key: "REDACTED"
body:
  email: "test@example.com"
  api_key: "REDACTED"
```

---

### Действие: `list`

Показать существующие кассеты.

```bash
# Все кассеты
find tests/fixtures/vcr -name "*.yaml" | wc -l

# По провайдеру
ls -la tests/fixtures/vcr/chembl/
ls -la tests/fixtures/vcr/uniprot/
ls -la tests/fixtures/vcr/pubmed/
ls -la tests/fixtures/vcr/pubchem/
ls -la tests/fixtures/vcr/crossref/
ls -la tests/fixtures/vcr/openalex/
ls -la tests/fixtures/vcr/semanticscholar/

# С размерами
du -sh tests/fixtures/vcr/*/
```

**Формат вывода:**
```
## VCR Cassettes

| Provider | Count | Size | Last Updated |
|----------|-------|------|--------------|
| chembl | 25 | 1.2 MB | 2026-02-01 |
| uniprot | 12 | 800 KB | 2026-01-28 |
| pubmed | 8 | 450 KB | 2026-01-25 |
| ... | ... | ... | ... |
| **Total** | **82** | **4.5 MB** | |
```

---

### Действие: `validate`

Проверить кассеты на наличие секретов.

```bash
# Поиск потенциальных секретов
grep -r -i -l "api_key\|apikey\|password\|secret\|token\|bearer\|auth" tests/fixtures/vcr/ --include="*.yaml"

# Поиск email (кроме тестовых)
grep -r -E "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}" tests/fixtures/vcr/ --include="*.yaml" | grep -v "test@\|example\|noreply"

# Поиск IP адресов
grep -r -E "\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b" tests/fixtures/vcr/ --include="*.yaml" | grep -v "127.0.0.1\|0.0.0.0"
```

**Формат вывода:**
```
## VCR Security Validation

### Potential Secrets Found
| File | Line | Issue |
|------|------|-------|
| chembl/test_fetch.yaml | 42 | Contains 'api_key' |
| uniprot/test_auth.yaml | 15 | Contains email pattern |

### Recommendations
1. Replace `api_key: "abc123"` with `api_key: "REDACTED"`
2. Replace real email with `test@example.com`

### Clean Files: 78/82
```

---

### Действие: `update`

Перезаписать существующую кассету.

```bash
# Удалить старую кассету
rm tests/fixtures/vcr/{provider}/test_name.yaml

# Записать новую (bash syntax)
VCR_RECORD_MODE=new_episodes uv run pytest tests/path/to/test.py::test_name -v -s

# Проверить
ls -la tests/fixtures/vcr/{provider}/test_name.yaml
```

---

### Действие: `clean`

Удалить устаревшие или неиспользуемые кассеты.

```bash
# Найти кассеты без соответствующих тестов
for cassette in tests/fixtures/vcr/**/*.yaml; do
    test_name=$(basename "$cassette" .yaml)
    if ! grep -r "def $test_name\|class $test_name" tests/ --include="*.py" -q; then
        echo "Orphan: $cassette"
    fi
done

# Найти кассеты старше N дней
find tests/fixtures/vcr -name "*.yaml" -mtime +90 -ls
```

---

## Структура VCR в проекте

```
tests/fixtures/vcr/
├── chembl/                    # 25 кассет
│   ├── TestChemblAdapter.test_fetch_activities.yaml
│   ├── TestChemblAdapter.test_health_check.yaml
│   └── ...
├── uniprot/                   # 12 кассет
│   ├── TestUniProtAdapterIntegration.test_fetch_proteins.yaml
│   └── ...
├── pubmed/                    # 8 кассет
├── pubchem/                   # 5 кассет
├── crossref/                  # 5 кассет
├── openalex/                  # 7 кассет
├── semanticscholar/           # 6 кассет
└── *.yaml                     # 14 cross-provider тестов
```

---

## Конфигурация VCR

**Файл:** `tests/conftest.py` (секция `VCR Configuration`, ~строка 130+)

### Автоматическая санитизация

Проект автоматически санитизирует:
- `email` → удаляется из query params
- `api_key`, `apikey` → удаляется из query params
- `retmode` → удаляется из query params

### Режимы записи

| Режим | Env Variable | Поведение |
|-------|--------------|-----------|
| `none` | `VCR_RECORD_MODE=none` | Fail if cassette missing (CI) |
| `new_episodes` | `VCR_RECORD_MODE=new_episodes` | Record new, replay existing |
| `once` | `VCR_RECORD_MODE=once` | Record once, then replay |
| `all` | `VCR_RECORD_MODE=all` | Always record (перезапись) |

### Custom Matcher

Игнорируемые параметры при матчинге:
```python
_VCR_IGNORED_QUERY_PARAMS = {"email", "api_key", "apikey", "retmode"}
```

---

## Пример полного workflow

```
User: /vcr-record test_fetch_activities

Claude: Записываю VCR-кассету для test_fetch_activities...

1. Поиск теста:
   $ grep -r "def test_fetch_activities" tests/
   → tests/integration/chembl/test_adapter.py:45

2. Провайдер: chembl
   Кассета: tests/fixtures/vcr/chembl/TestChemblAdapter.test_fetch_activities.yaml

3. Запись:
   $ VCR_RECORD_MODE=new_episodes pytest tests/integration/chembl/test_adapter.py::TestChemblAdapter::test_fetch_activities -v -s

   PASSED

4. Валидация:
   $ grep -i "api_key\|secret" tests/fixtures/vcr/chembl/TestChemblAdapter.test_fetch_activities.yaml
   (no matches - OK)

5. Результат:
   ✅ Кассета записана: tests/fixtures/vcr/chembl/TestChemblAdapter.test_fetch_activities.yaml
   📦 Размер: 12.5 KB
   🔒 Секреты: не найдены

   Для воспроизведения:
   $ pytest tests/integration/chembl/test_adapter.py::TestChemblAdapter::test_fetch_activities -v
```

---

## Troubleshooting

### Кассета не записывается

```bash
# Проверить что VCR включен
python -c "import vcr; print('VCR OK')"

# Проверить режим
echo $VCR_RECORD_MODE

# Запустить с verbose
pytest test.py -v -s --tb=long
```

### Тест не находит кассету

```bash
# Проверить путь кассеты
ls -la tests/fixtures/vcr/{provider}/

# Проверить имя (должно совпадать с TestClass.test_method)
# Пример: TestChemblAdapter.test_fetch_activities.yaml
```

### Кассета содержит секреты

```bash
# Автоматическая санитизация
python -c "
import yaml
with open('cassette.yaml') as f:
    data = yaml.safe_load(f)
# Редактировать data
with open('cassette.yaml', 'w') as f:
    yaml.dump(data, f)
"
```

---

## Best Practices

1. **Naming**: `TestClassName.test_method_name.yaml`
2. **Location**: `tests/fixtures/vcr/{provider}/`
3. **Size**: Минимизировать response body (только нужные поля)
4. **Secrets**: Всегда проверять перед коммитом
5. **CI**: Всегда `VCR_RECORD_MODE=none`
6. **Updates**: Перезаписывать при изменении API
