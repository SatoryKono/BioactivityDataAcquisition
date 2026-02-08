# AI Self-Review Rules

*Версия: 1.1.0 | Синхронизировано с RULES.md v5.17 (2026-02-03)*

Правила для автоматической самопроверки кода в проекте BioETL.
Использует RFC 2119 keywords: **MUST**, **SHOULD**, **MAY**.

---

## Quick Reference

| Категория | Severity | Правила |
|-----------|----------|---------|
| Architecture | CRITICAL | ARCH-001...ARCH-008 |
| Anti-Patterns | CRITICAL/HIGH | AP-001...AP-008 |
| DI Violations | CRITICAL | DI-001...DI-005 |
| Naming | MEDIUM | NAME-001...NAME-006 |
| Types | HIGH | TYPE-001...TYPE-004 |
| Testing | HIGH | TEST-001...TEST-005 |
| Exceptions | INFO | EXC-001...EXC-015 |

---

## 1. Архитектурные Правила (ARCH)

### ARCH-001: Матрица Импортов (CRITICAL)

**MUST** соблюдать матрицу импортов между слоями.

| From \ To | domain | application | infrastructure | composition | interfaces |
|-----------|--------|-------------|----------------|-------------|------------|
| **domain** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **application** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **infrastructure** | ✅ | ❌ | ✅ | ❌ | ❌ |
| **composition** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **interfaces** | ✅ | ✅ | ✅ | ✅ | ✅ |

> **Примечание:** Infrastructure может импортировать любые domain-модули (ports, types,
> exceptions, entities, config, models, value_objects, serialization и т.д.).
> Domain содержит чистую бизнес-логику без I/O — это value objects и контракты,
> от которых infrastructure зависит by design. Ports **MUST** импортироваться
> только через фасад `bioetl.domain.ports` (ARCH-008).

**Детекция:**
```bash
# domain → infrastructure (НАРУШЕНИЕ)
grep -rn "from bioetl.infrastructure" src/bioetl/domain/ --include="*.py"

# application → infrastructure (НАРУШЕНИЕ)
grep -rn "from bioetl.infrastructure" src/bioetl/application/ --include="*.py" | grep -v TYPE_CHECKING

# infrastructure → application (НАРУШЕНИЕ)
grep -rn "from bioetl.application" src/bioetl/infrastructure/ --include="*.py" | grep -v TYPE_CHECKING

# infrastructure → composition (НАРУШЕНИЕ)
grep -rn "from bioetl.composition" src/bioetl/infrastructure/ --include="*.py"

# infrastructure → interfaces (НАРУШЕНИЕ)
grep -rn "from bioetl.interfaces" src/bioetl/infrastructure/ --include="*.py"
```

**Исправление:** Перенести зависимость в правильный слой или использовать Port protocol.

---

### ARCH-002: Domain Purity (CRITICAL)

**MUST NOT** содержать I/O операции в domain слое.

**Запрещено в domain:**
- `import requests`, `import httpx`, `import aiohttp`
- `open(`, `Path().read_`, `Path().write_`
- `import structlog` (использовать LoggerPort)
- Database clients, file operations

**Детекция:**
```bash
grep -rn "import requests\|import httpx\|open(\|\.read_text\|\.write_" src/bioetl/domain/ --include="*.py"
```

---

### ARCH-003: Port Protocol Naming (HIGH)

Все Ports **MUST** быть определены как `typing.Protocol` в `domain/ports/`.

**Naming:**
- Имя класса: `*Port` suffix
- Модуль: `domain/ports/{name}_port.py`

**Детекция:**
```bash
# Protocols без Port suffix
grep -rn "class.*Protocol\):" src/bioetl/domain/ports/ | grep -v "Port"
```

---

### ARCH-004: Adapter Health Check (HIGH)

Все HTTP/External адаптеры **MUST** реализовывать `health_check()`.

```python
async def health_check(self) -> HealthStatus:
    """MUST быть async, MUST возвращать HealthStatus enum."""
```

**Детекция:**
```bash
# Адаптеры без health_check
for f in src/bioetl/infrastructure/adapters/**/client.py; do
  grep -L "def health_check\|async def health_check" "$f"
done
```

---

### ARCH-005: Composition Root Isolation (HIGH)

Factory и assembly логика **MUST** находиться только в `composition/`.

**Детекция:**
```bash
# Factory вызовы вне composition
grep -rn "Factory\(\)" src/bioetl/application/ src/bioetl/domain/ --include="*.py"
```

---

### ARCH-006: Silver Layer ACID (CRITICAL)

**MUST** использовать Delta Lake для Silver слоя. Raw Parquet **MUST NOT** использоваться.

**Детекция:**
```bash
grep -rn "to_parquet\|write_parquet" src/bioetl/infrastructure/storage/silver/ --include="*.py"
```

---

### ARCH-007: Medallion Clear Policy (CRITICAL)

| Run Type | Clear Silver | Clear Gold |
|----------|--------------|------------|
| REBUILD | ✅ MUST | ✅ MUST |
| BACKFILL | ✅ MUST | ✅ MUST |
| INCREMENTAL | ❌ MUST NOT | ❌ MUST NOT |

**Детекция:** Проверить логику `clear_silver()`, `clear_gold()` с `run_type`.

---

### ARCH-008: Single Source of Imports (MEDIUM)

Ports **MUST** импортироваться из фасада `bioetl.domain.ports`, а не из внутренних модулей.

**Правильно:**
```python
from bioetl.domain.ports import DataSourcePort
```

**Неправильно:**
```python
from bioetl.domain.ports.data_source_port import DataSourcePort
```

---

## 2. Антипаттерны (AP)

### AP-001: DI Violation — Hard-coded Constructor (CRITICAL)

**MUST NOT** создавать concrete dependencies внутри класса.

**Неправильно:**
```python
class MyService:
    def __init__(self):
        self.client = HTTPClient()  # ❌ Hard-coded
```

**Правильно:**
```python
class MyService:
    def __init__(self, client: HTTPClientPort):
        self._client = client  # ✅ Injected
```

**Детекция:**
```bash
grep -rn "self\.[a-z_]* = [A-Z][a-zA-Z]*(" src/bioetl/application/ src/bioetl/domain/ --include="*.py"
```

---

### AP-002: Direct structlog Import (HIGH)

**MUST NOT** импортировать structlog напрямую в application/interfaces.
Использовать `LoggerPort`.

**Детекция:**
```bash
grep -rn "import structlog" src/bioetl/application/ src/bioetl/interfaces/ --include="*.py"
```

**Исключение:** `infrastructure/observability/` — здесь реализация LoggerPort.

---

### AP-003: Import Boundary Violation (CRITICAL)

См. ARCH-001. Нарушение матрицы импортов.

---

### AP-004: Sentinel Values (MEDIUM)

**SHOULD NOT** использовать sentinel values. Использовать `None` / `Optional`.

**Плохо:**
```python
value = -1  # означает "нет значения"
status = "N/A"
count = 9999  # magic number
```

**Хорошо:**
```python
value: int | None = None
```

**Детекция:**
```bash
grep -rn '= -1\|"N/A"\|"n/a"\|= 9999' src/bioetl/ --include="*.py"
```

---

### AP-005: Hardcoded Secrets (CRITICAL)

**MUST NOT** хардкодить credentials в коде.

**Детекция:**
```bash
grep -rn "password\s*=\s*[\"']\|api_key\s*=\s*[\"']\|secret\s*=\s*[\"']" src/bioetl/ --include="*.py"
```

**Исключение:** Test fixtures, Port/Protocol definitions.

---

### AP-006: Print Statements (MEDIUM)

**SHOULD NOT** использовать `print()`. Использовать structured logging.

**Детекция:**
```bash
grep -rn "^\s*print(" src/bioetl/ --include="*.py"
```

**Исключение:** CLI output в `interfaces/cli/`.

---

### AP-007: Raw Parquet in Silver (CRITICAL)

**MUST** использовать Delta Lake для Silver. См. ARCH-006.

---

### AP-008: Blocking I/O in Async (HIGH)

**MUST NOT** использовать blocking I/O в async функциях.

**Плохо:**
```python
async def fetch_data():
    with open("file.txt") as f:  # ❌ Blocking
        return f.read()
```

**Хорошо:**
```python
async def fetch_data():
    return await asyncio.to_thread(read_file, "file.txt")  # ✅ Non-blocking
```

**Детекция:**
```bash
# Поиск open() в async функциях
grep -A5 "async def" src/bioetl/ -r --include="*.py" | grep "open(\|requests\.\|urllib"
```

---

## 3. DI Violations (DI)

### DI-001: Hard-coded Constructor (CRITICAL)

```python
# ❌ НАРУШЕНИЕ
self.client = ConcreteHTTPClient()

# ✅ ПРАВИЛЬНО
def __init__(self, client: HTTPClientPort):
    self._client = client
```

---

### DI-002: Method-level Instantiation (CRITICAL)

```python
# ❌ НАРУШЕНИЕ
def process(self):
    client = HTTPClient()  # Создаёт внутри метода
    return client.fetch()

# ✅ ПРАВИЛЬНО
def process(self):
    return self._client.fetch()  # Использует injected
```

---

### DI-003: Service Locator (CRITICAL)

**MUST NOT** использовать Service Locator pattern.

```python
# ❌ НАРУШЕНИЕ
client = ServiceLocator.get(HTTPClient)
service = Container.resolve("MyService")

# ✅ ПРАВИЛЬНО — Constructor Injection
def __init__(self, client: HTTPClientPort):
    self._client = client
```

**Детекция:**
```bash
grep -rn "ServiceLocator\|Container\.resolve\|Container\.get" src/bioetl/ --include="*.py"
```

---

### DI-004: Import-time Side Effects (HIGH)

**MUST NOT** иметь side effects на уровне модуля (кроме tests).

```python
# ❌ НАРУШЕНИЕ (module level)
logger = structlog.get_logger()
config = load_config()
client = HTTPClient()

# ✅ ПРАВИЛЬНО — в конструкторе или factory
class MyService:
    def __init__(self, logger: LoggerPort):
        self._logger = logger
```

**Детекция:**
```bash
grep -rn "^[a-z_]* = [A-Z][a-zA-Z]*(" src/bioetl/application/ src/bioetl/domain/ --include="*.py"
```

---

### DI-005: Factory in Business Logic (HIGH)

Factory вызовы **MUST** быть только в `composition/`.

```python
# ❌ НАРУШЕНИЕ (в application)
def run_pipeline():
    runner = PipelineFactory.create()

# ✅ ПРАВИЛЬНО (в composition)
# composition/bootstrap/assembly.py
runner = PipelineFactory.create()
```

---

## 4. Naming Conventions (NAME)

### NAME-001: Class Suffixes (MUST)

| Тип | Suffix | Пример |
|-----|--------|--------|
| Factory | `*Factory` | `PipelineFactory` |
| Client | `*Client` | `ChEMBLClient` |
| Protocol/Port | `*Port` | `DataSourcePort` |
| Service | `*Service` | `ValidationService` |
| Transformer | `*Transformer` | `CompoundTransformer` |
| Adapter | `*Adapter` | `BaseHttpAdapter` |
| Error/Exception | `*Error` | `ValidationError` |
| Schema | `*Schema` | `CompoundGoldSchema` |
| Config | `*Config` | `RuntimeConfig` |

**Детекция:**
```bash
# Классы без proper suffix в application
grep -rn "^class [A-Z][a-zA-Z]*:" src/bioetl/application/ --include="*.py" | \
  grep -v "Factory\|Service\|Transformer\|Error\|Config\|Protocol\|Port"
```

---

### NAME-002: Function Prefixes (SHOULD)

| Prefix | Назначение | Пример |
|--------|------------|--------|
| `get_*` | Локальные данные | `get_config()` |
| `fetch_*` | Сетевые/I/O операции | `fetch_compounds()` |
| `iter_*` | Генераторы | `iter_records()` |
| `create_*` | Создание объектов | `create_pipeline()` |
| `build_*` | Сложная сборка | `build_query()` |
| `validate_*` | Валидация | `validate_schema()` |
| `is_*` | Boolean query | `is_valid()` |
| `has_*` | Boolean query | `has_permission()` |
| `can_*` | Boolean query | `can_process()` |

---

### NAME-003: Module Naming (MUST)

- snake_case
- Без сокращений
- Описательные имена
- Single responsibility

**Хорошо:** `delta_writer.py`, `bronze_writer.py`, `record_processor.py`
**Плохо:** `dw.py`, `utils.py`, `helpers.py`, `misc.py`

---

### NAME-004: Private Attributes (SHOULD)

Private атрибуты **SHOULD** использовать single underscore prefix.

```python
class MyService:
    def __init__(self, client: ClientPort):
        self._client = client  # ✅ Single underscore
```

---

### NAME-005: Constants (MUST)

Constants **MUST** быть UPPER_SNAKE_CASE.

```python
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30.0
API_BASE_URL = "https://api.example.com"
```

---

### NAME-006: Enum Values (MUST)

Enum members **MUST** быть UPPER_SNAKE_CASE.

```python
class RunType(Enum):
    INCREMENTAL = "incremental"
    BACKFILL = "backfill"
    REBUILD = "rebuild"
```

---

## 5. Type Annotations (TYPE)

### TYPE-001: Public Function Annotations (MUST)

Все публичные функции и методы **MUST** иметь type annotations.

```python
# ❌ НАРУШЕНИЕ
def process(data):
    return data

# ✅ ПРАВИЛЬНО
def process(data: list[dict[str, Any]]) -> ProcessedData:
    return ProcessedData(data)
```

**Детекция:**
```bash
# Публичные функции без return type
grep -rn "def [^_].*):$" src/bioetl/ --include="*.py" | grep -v "-> "
```

---

### TYPE-002: Any Usage (SHOULD)

`Any` **SHOULD NOT** использоваться без обоснования в комментарии.

```python
# ❌ НАРУШЕНИЕ
def process(data: Any) -> Any:
    pass

# ✅ ПРАВИЛЬНО (с обоснованием)
def process(data: Any) -> Any:  # Any: external API returns untyped JSON
    pass
```

**Детекция:**
```bash
grep -rn ": Any\|-> Any" src/bioetl/ --include="*.py" | grep -v "#.*Any"
```

---

### TYPE-003: mypy Strict (MUST)

Код **MUST** проходить `mypy --strict`.

```bash
mypy --strict src/bioetl/
```

---

### TYPE-004: Protocol Runtime Checkable (SHOULD)

Critical Ports **SHOULD** быть `@runtime_checkable` для boundary validation.

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class DataSourcePort(Protocol):
    def fetch(self, query: Query) -> Iterator[RawRecord]: ...
```

---

## 6. Testing Rules (TEST)

### TEST-001: Coverage Threshold (MUST)

Code coverage **MUST** быть ≥85%.

```bash
pytest --cov=src/bioetl --cov-fail-under=85
```

---

### TEST-002: Unit Tests for New Code (MUST)

Новый код **MUST** иметь unit tests в `tests/unit/{layer}/{module}/`.

---

### TEST-003: VCR Cassettes for HTTP (MUST)

HTTP tests **MUST** использовать VCR.py cassettes.

- Location: `tests/fixtures/vcr/{provider}/`
- One cassette per test function
- Sanitize secrets in `before_record` callback

---

### TEST-004: Architecture Tests (MUST)

Изменения в import структуре **MUST** проходить architecture tests.

```bash
pytest tests/architecture/ -v
```

---

### TEST-005: No Test Logic in Production (MUST)

Test-specific код **MUST NOT** быть в production code.

**Детекция:**
```bash
grep -rn "if.*test\|pytest\|unittest" src/bioetl/ --include="*.py" | grep -v "# noqa"
```

---

## 7. Исключения — НЕ Нарушения (EXC)

> **КРИТИЧЕСКИ ВАЖНО:** Эти паттерны **НЕ являются нарушениями**!
> Проверять перед флагом проблемы.

### EXC-001: TYPE_CHECKING Imports

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.infrastructure import SomeAdapter  # ✅ OK — type hints only
```

---

### EXC-002: Optional Parameters with Defaults

```python
class MyService:
    def __init__(
        self,
        client: ClientPort,
        policy: Policy | None = None,  # ✅ OK — valid DI pattern
        timeout: float = 30.0,  # ✅ OK — configuration value
    ):
        self._client = client
        self._policy = policy or DefaultPolicy()
```

---

### EXC-003: NoOp Implementations (Null Object Pattern)

```python
class NoOpTracing(TracingPort):
    def start_span(self, name: str) -> Span:
        return NoOpSpan()  # ✅ OK — Null Object Pattern
```

---

### EXC-004: Re-exports for Compatibility

```python
# application/core/medallion_policy.py
from bioetl.domain.policies import MedallionPolicy

__all__ = ["MedallionPolicy"]  # ✅ OK — backward compatibility
```

---

### EXC-005: Large Files with Delegation

Файл 500+ LOC **НЕ** god object если:
- Много `self._component.method()` вызовов
- Proper responsibility delegation
- High cohesion

**Проверка:**
```bash
# Количество delegation calls
grep -o "self\._[a-z_]*\." file.py | sort -u | wc -l
# Если > 5 — likely NOT god object
```

---

### EXC-006: Graceful Degradation

```python
def _get_memory_stats(self) -> MemoryStats:
    try:
        return self._get_real_stats()
    except ImportError:
        return self._get_conservative_estimate()  # ✅ OK — graceful fallback
```

---

### EXC-007: Int→Float Coercion in Gold Schemas

```python
class CompoundGoldSchema(pa.DataFrameModel):
    record_id: Series[float] = pa.Field(coerce=True)  # ✅ OK — nullable int handling
```

**Причина:** Pandas исторически не поддерживал nullable integers без `Int64`.

---

### EXC-008: Click for CLI

```python
@click.command()
@click.option("--verbose", is_flag=True)
def main(verbose: bool) -> None:  # ✅ OK — intentional choice over Typer
    pass
```

---

### EXC-009: CLI Confirmations

```python
# interfaces/cli/commands.py
if not click.confirm("Proceed?"):  # ✅ OK — interfaces layer responsibility
    raise click.Abort()
```

---

### EXC-010: Email in Config

```python
# ✅ OK — technical identifier for NCBI API, NOT PII
default_email: str = "bioetl@example.com"
```

---

### EXC-011: MemoryLock Sufficiency

```python
# ✅ OK — sufficient for local-only deployment (ADR-010)
lock = MemoryLock(key=f"lock:{provider}_{entity}")
```

---

### EXC-012: All domain imports in Infrastructure

```python
# infrastructure/adapters/chembl/client.py
from bioetl.domain.ports import DataSourcePort  # ✅ OK — Port protocols are contracts
from bioetl.domain.entities import Molecule       # ✅ OK — domain value objects
from bioetl.domain.config import PipelineConfig   # ✅ OK — domain configuration
from bioetl.domain.types import HealthStatus      # ✅ OK — shared type definitions
from bioetl.domain.exceptions import ValidationError  # ✅ OK — shared exceptions
```

Infrastructure зависит от domain by design — domain содержит чистые value objects,
entities, config и contracts (ports) без I/O. Это штатная зависимость по Hexagonal
Architecture: adapters реализуют domain ports и работают с domain entities.

---

### EXC-013: domain.types and domain.exceptions Everywhere

```python
# Anywhere in codebase (all layers)
from bioetl.domain.types import HealthStatus  # ✅ OK — shared definitions
from bioetl.domain.exceptions import ValidationError  # ✅ OK — shared definitions
```

---

### EXC-014: Test-specific Module-level Assignments

```python
# tests/unit/test_something.py
logger = structlog.get_logger()  # ✅ OK — allowed in tests
```

---

### EXC-015: Config Classes with Defaults

```python
@dataclass
class RuntimeConfig:
    timeout: float = 30.0  # ✅ OK — configuration value object
    max_retries: int = 3
```

---

## Scoring Matrix

| Category | Weight | Max Score |
|----------|--------|-----------|
| Architecture (ARCH) | 30% | 10 |
| Anti-Patterns (AP) | 25% | 10 |
| DI Violations (DI) | 20% | 10 |
| Naming (NAME) | 10% | 10 |
| Types (TYPE) | 10% | 10 |
| Testing (TEST) | 5% | 10 |

### Severity Impact on Score

| Severity | Deduction per Issue |
|----------|---------------------|
| CRITICAL | -2.0 |
| HIGH | -1.0 |
| MEDIUM | -0.5 |
| LOW | -0.25 |

### Status Thresholds

| Score | Status |
|-------|--------|
| ≥ 8.0 | PASS |
| 6.0 - 7.9 | WARN |
| < 6.0 | FAIL |

---

## Verification Commands

```bash
# Full lint check
make lint

# Type check
mypy --strict src/bioetl/

# Architecture tests
pytest tests/architecture/ -v

# Coverage check
pytest --cov=src/bioetl --cov-fail-under=85

# Import boundary check
importlinter

# Security scan
make security
```

---

## References

- **RULES.md** — `docs/00-project/RULES.md`
- **CLAUDE.md** — `docs/00-project/agents/CLAUDE.md`
- **ADR Documents** — `docs/02-architecture/decisions/`
- **Agent Prompts** — `.claude/agents/`

---

*Версия документа синхронизирована с RULES.md. При обновлении RULES.md обновить этот документ.*
