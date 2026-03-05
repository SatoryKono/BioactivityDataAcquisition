---
description: "Запись и управление VCR-кассетами для HTTP-тестов BioETL. Действия: record, list, validate, update, clean."
---

# /vcr-record

## Использование
```
/vcr-record [action] [target]
```

**Действия:** `record` (default), `list`, `validate`, `update`, `clean`
**Target:** test name, provider, or file path.

## Инструкции

### record (default)
1. Find test: `grep -r "def {test_name}" tests/ --include="*.py" -l`
2. Determine provider from path
3. Record: `VCR_RECORD_MODE=new_episodes uv run pytest {test_path}::{test} -v -s`
4. Validate: `grep -i "api_key\|password\|secret\|token" tests/fixtures/vcr/{provider}/*.yaml`
5. Sanitize if needed: replace real values with `REDACTED`

### list
```bash
find tests/fixtures/vcr -name "*.yaml" | wc -l
du -sh tests/fixtures/vcr/*/
```

### validate
```bash
grep -r -i -l "api_key\|apikey\|password\|secret\|token\|bearer" tests/fixtures/vcr/ --include="*.yaml"
grep -r -E "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}" tests/fixtures/vcr/ --include="*.yaml" | grep -v "test@\|example\|noreply"
```

### update
```bash
rm tests/fixtures/vcr/{provider}/{test_name}.yaml
VCR_RECORD_MODE=new_episodes uv run pytest {test_path}::{test} -v -s
```

### clean
```bash
# Orphan cassettes (no matching test)
for cassette in tests/fixtures/vcr/**/*.yaml; do
    test_name=$(basename "$cassette" .yaml)
    grep -r "def $test_name\|class $test_name" tests/ --include="*.py" -q || echo "Orphan: $cassette"
done
# Old cassettes
find tests/fixtures/vcr -name "*.yaml" -mtime +90 -ls
```

## VCR Config
- Config location: `tests/conftest.py` (~line 130+)
- Auto-sanitized params: `email`, `api_key`, `apikey`, `retmode`
- Modes: `none` (CI), `new_episodes` (record new), `once`, `all` (overwrite)
- Cassette naming: `TestClassName.test_method_name.yaml`
- Location: `tests/fixtures/vcr/{provider}/`
