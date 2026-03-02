# vcr-tests — VCR Test Task Generator

*Priority: medium | Version: 1.0 | Aligned with RULES.md v5.23*

______________________________________________________________________

## Goal

Analyze the crosswalk diff (output of `01-xwalk.md`) to determine which VCR cassettes need to be recorded or updated, and generate a task list with deterministic VCR recording instructions.

______________________________________________________________________

## Input

| Parameter    | Source                                                                          | Example                     |
| ------------ | ------------------------------------------------------------------------------- | --------------------------- |
| `{{source}}` | User argument                                                                   | `chembl`, `chembl/activity` |
| xwalk diff   | Output of `01-xwalk.md` or git diff of xwalk CSV                                | Changed/added fields        |
| existing VCR | `tests/fixtures/vcr/{{provider}}/`                                              | Current cassettes           |
| test files   | `tests/integration/{{provider}}/` or `tests/integration/adapters/{{provider}}/` | Existing integration tests  |

______________________________________________________________________

## Output

- **Task list** in Markdown: which cassettes to record/update
- **VCR recording commands** ready to execute

______________________________________________________________________

## Algorithm

### 1. Parse xwalk diff

From the crosswalk output, identify:

- **New fields** (present in code, absent from previous xwalk)
- **Removed fields** (present in previous xwalk, absent from code)
- **Type changes** (field type changed)
- **Renamed fields** (RENAME note in xwalk)

### 2. Map fields to API responses

For each changed field, determine:

- Which API endpoint returns it
- Which integration test covers that endpoint
- Which VCR cassette records that response

### 3. Classify VCR actions

| Action     | Trigger                                | Command                     |
| ---------- | -------------------------------------- | --------------------------- |
| **RECORD** | New field not in any cassette          | Record new cassette         |
| **UPDATE** | Field type/name changed                | Delete + re-record cassette |
| **VERIFY** | Field exists but cassette may be stale | Replay and check            |
| **NO-OP**  | No change to API-facing fields         | Skip                        |

### 4. Generate task list

````markdown
## VCR Tasks: {{source}}

### Summary

| Action | Count | Cassettes |
|--------|-------|-----------|
| RECORD | 2 | test_fetch_new_entity.yaml, test_health_check.yaml |
| UPDATE | 1 | TestAdapter.test_fetch_activities.yaml |
| VERIFY | 3 | ... |
| NO-OP | 12 | ... |

### Tasks

#### 1. [RECORD] {{provider}}/test_fetch_{{entity}}.yaml

**Reason:** New entity `{{entity}}` added, no cassette exists.

**Prerequisites:**
- [ ] API is accessible (check health: `curl {{health_endpoint}}`)
- [ ] VCR record mode available

**Commands:**
```bash
export VCR_RECORD_MODE=new_episodes
pytest tests/integration/{{provider}}/test_{{entity}}.py -v -s
export VCR_RECORD_MODE=none
````

**Post-record:**

- [ ] Verify cassette created: `ls tests/fixtures/vcr/{{provider}}/`
- [ ] Check for secrets: `grep -i "api_key\|secret\|token" tests/fixtures/vcr/{{provider}}/test_*.yaml`
- [ ] Replay test: `pytest tests/integration/{{provider}}/test_{{entity}}.py -v`

#### 2. [UPDATE] {{provider}}/TestAdapter.test_fetch_activities.yaml

**Reason:** Field `{{field}}` renamed from `{{old_name}}` to `{{new_name}}`.

**Commands:**

```bash
rm tests/fixtures/vcr/{{provider}}/TestAdapter.test_fetch_activities.yaml
export VCR_RECORD_MODE=new_episodes
pytest tests/integration/{{provider}}/test_adapter.py::TestAdapter::test_fetch_activities -v -s
export VCR_RECORD_MODE=none
```

````

### 5. Detect missing integration tests

If a field change has no corresponding integration test:

```markdown
### Missing Integration Tests

| Entity | Field | Reason | Suggested Test |
|--------|-------|--------|---------------|
| {{entity}} | {{field}} | No integration test covers this field | `test_fetch_{{entity}}_includes_{{field}}` |
````

______________________________________________________________________

## Architecture Compliance

- VCR cassettes MUST be in `tests/fixtures/vcr/{{provider}}/` (TEST-003)
- One cassette per test function
- Secrets MUST be sanitized via `before_record` callback (configured in `tests/conftest.py`)
- CI MUST run with `VCR_RECORD_MODE=none`

______________________________________________________________________

## Commit & PR Convention (`{{C}}`)

- **Branch:** `test/{{source}}-vcr`
- **PR title:** `test({{source}}): update VCR cassettes`
- **Labels:** `test`

______________________________________________________________________

## Example

For `chembl` after adding `tpsa` to molecule:

````markdown
## VCR Tasks: chembl

### Tasks

#### 1. [UPDATE] chembl/TestChemblAdapter.test_fetch_molecules.yaml

**Reason:** Field `tpsa` added to molecule transformer — cassette may not include this field.

**Commands:**
```bash
rm tests/fixtures/vcr/chembl/TestChemblAdapter.test_fetch_molecules.yaml
export VCR_RECORD_MODE=new_episodes
pytest tests/integration/chembl/test_adapter.py::TestChemblAdapter::test_fetch_molecules -v -s
export VCR_RECORD_MODE=none
````

```

---

## Constraints

- Do NOT record cassettes automatically. This prompt generates the task list only.
- VCR recording requires network access — document prerequisites clearly.
- Cassette naming MUST follow pattern: `TestClassName.test_method_name.yaml`.
- If no integration test directory exists for a provider, flag it as a gap.


## ADR Status Guardrail

- Перед выводами по ADR пересчитать baseline как фактическое количество файлов `docs/02-architecture/decisions/ADR-*.md` (не фиксировать число вручную).
- Разрешённые базовые статусы ADR: `Accepted`, `Superseded`, `Deprecated`, `Added`.
- `Superseded` НЕ считать автоматическим дефектом: это нормальная эволюция архитектуры при наличии ADR-замены/контекста.
- Дефектом считать только отсутствие статуса, невалидный статус или `Superseded` без связи с заменяющим ADR.
```
