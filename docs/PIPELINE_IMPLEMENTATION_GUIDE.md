# Руководство по реализации пайплайнов

Данный документ содержит подробные инструкции по:
1. Добавлению нового пайплайна для существующего провайдера (ChEMBL)
2. Добавлению нового провайдера данных (PubChem)

---

## Часть 1: Добавление нового ChEMBL пайплайна (например, Document)

### Обзор архитектуры

Проект использует **Hexagonal Architecture** (Ports & Adapters) с 4 слоями:

```
┌─────────────────────────────────────────────────────────────┐
│                    INTERFACES LAYER                         │
│              (CLI, REST API - внешние границы)              │
├─────────────────────────────────────────────────────────────┤
│                   APPLICATION LAYER                         │
│     (Оркестрация, DI Container, Pipelines, Factories)      │
├─────────────────────────────────────────────────────────────┤
│                  INFRASTRUCTURE LAYER                       │
│      (HTTP клиенты, файловые операции, внешние API)        │
├─────────────────────────────────────────────────────────────┤
│                     DOMAIN LAYER                            │
│    (Бизнес-логика, Ports/ABCs, Models, Value Objects)      │
└─────────────────────────────────────────────────────────────┘
```

### Шаг 1: Создание конфигурации пайплайна

**Файл:** `configs/pipelines/chembl/<entity>.yaml`

```yaml
# configs/pipelines/chembl/document.yaml

# Идентификатор пайплайна в формате provider.entity
id: chembl.document
provider: chembl
entity: document
primary_key: "${CHEMBL_DOCUMENT_PRIMARY_KEY:-document_chembl_id}"

# Режим ввода: id_only (по ID из CSV), csv (полный CSV), api (напрямую из API)
input_mode: id_only
input_path: data/input/document.csv
output_path: ./data/output/chembl/document
batch_size: 50

# Конфигурация провайдера
provider_config:
  provider: chembl
  base_url: https://www.ebi.ac.uk/chembl/api/data
  client:
    timeout_sec: 30.0
    max_retries: 3
    rate_limit_per_sec: 10.0
  max_url_length: 2000
  batch_size: 50
  page_size: 1000
  api_version: null

# Опции CSV
csv_options:
  delimiter: ","
  header: true

# Метаданные пайплайна
pipeline:
  name: document_chembl
  version: "1.0.0"
  owner: "Data Acquisition Team"
  description: "Extract document/publication records from ChEMBL API"
  enable_denormalization: false

# Настройки трансформации
transform:
  serialization_mode: pipe

# Определение полей схемы (из API документации ChEMBL)
fields:
  - name: document_chembl_id
    data_type: string
    is_nullable: false
    is_filterable: true
    description: "ChEMBL ID документа"

  - name: doc_type
    data_type: string
    is_nullable: true
    is_filterable: true
    description: "Тип документа (PUBLICATION, PATENT, etc.)"

  - name: title
    data_type: string
    is_nullable: true
    is_filterable: false
    description: "Заголовок публикации"

  - name: authors
    data_type: string
    is_nullable: true
    is_filterable: false
    description: "Авторы публикации"

  - name: journal
    data_type: string
    is_nullable: true
    is_filterable: true
    description: "Название журнала"

  - name: year
    data_type: integer
    is_nullable: true
    is_filterable: true
    description: "Год публикации"

  - name: volume
    data_type: string
    is_nullable: true
    is_filterable: false
    description: "Том журнала"

  - name: issue
    data_type: string
    is_nullable: true
    is_filterable: false
    description: "Номер выпуска"

  - name: first_page
    data_type: string
    is_nullable: true
    is_filterable: false
    description: "Первая страница"

  - name: last_page
    data_type: string
    is_nullable: true
    is_filterable: false
    description: "Последняя страница"

  - name: pubmed_id
    data_type: integer
    is_nullable: true
    is_filterable: true
    description: "PubMed ID"

  - name: doi
    data_type: string
    is_nullable: true
    is_filterable: true
    description: "DOI публикации"

  - name: patent_id
    data_type: string
    is_nullable: true
    is_filterable: true
    description: "ID патента"

  - name: abstract
    data_type: string
    is_nullable: true
    is_filterable: false
    description: "Абстракт публикации"

# Настройки качества данных
quality:
  hashing:
    business_key_fields:
      - document_chembl_id
  normalization:
    case_sensitive_fields:
      - doc_type
      - doi
    id_fields:
      - document_chembl_id
      - pubmed_id
      - patent_id
      - doi
```

### Шаг 2: Добавление endpoint mapping (если нужен новый endpoint)

**Файл:** `src/bioetl/infrastructure/clients/chembl/constants.py`

```python
# Если entity "document" еще не определен в ENTITY_TO_ENDPOINT
ENTITY_TO_ENDPOINT: dict[str, str] = {
    "activity": "activity",
    "assay": "assay",
    "molecule": "molecule",
    "target": "target",
    "document": "document",  # <-- Добавить если отсутствует
    # ...
}
```

### Шаг 3: Регистрация пайплайна в реестре

**Файл:** `src/bioetl/application/pipelines/registry.py`

```python
from bioetl.application.pipelines.chembl.factories import ChemblPipelineFactory

# Добавить в словарь _FACTORIES
_FACTORIES: dict[str, PipelineFactoryABC] = {
    "chembl.activity": ChemblPipelineFactory(),
    "chembl.assay": ChemblPipelineFactory(),
    "chembl.molecule": ChemblPipelineFactory(),
    "chembl.target": ChemblPipelineFactory(),
    "chembl.document": ChemblPipelineFactory(),  # <-- Добавить
    # ...
}
```

### Шаг 4: Добавление схемы контракта (опционально)

**Файл:** `src/bioetl/domain/schemas/contracts/chembl_document.py`

```python
"""Schema contract for ChEMBL document entity."""

from bioetl.domain.schemas.pipeline_contracts import PipelineSchemaModel, FieldSchema

CHEMBL_DOCUMENT_CONTRACT = PipelineSchemaModel(
    pipeline_id="chembl.document",
    entity="document",
    fields=[
        FieldSchema(name="document_chembl_id", dtype="string", nullable=False),
        FieldSchema(name="doc_type", dtype="string", nullable=True),
        FieldSchema(name="title", dtype="string", nullable=True),
        FieldSchema(name="authors", dtype="string", nullable=True),
        FieldSchema(name="journal", dtype="string", nullable=True),
        FieldSchema(name="year", dtype="Int64", nullable=True),
        FieldSchema(name="volume", dtype="string", nullable=True),
        FieldSchema(name="issue", dtype="string", nullable=True),
        FieldSchema(name="first_page", dtype="string", nullable=True),
        FieldSchema(name="last_page", dtype="string", nullable=True),
        FieldSchema(name="pubmed_id", dtype="Int64", nullable=True),
        FieldSchema(name="doi", dtype="string", nullable=True),
        FieldSchema(name="patent_id", dtype="string", nullable=True),
        FieldSchema(name="abstract", dtype="string", nullable=True),
    ],
)
```

Затем зарегистрировать в `src/bioetl/domain/schemas/pipeline_contracts.py`:

```python
from bioetl.domain.schemas.contracts.chembl_document import CHEMBL_DOCUMENT_CONTRACT

_CONTRACTS["chembl.document"] = CHEMBL_DOCUMENT_CONTRACT
```

### Шаг 5: Создание тестов

**Файл:** `tests/bioetl/application/pipelines/chembl/test_document_pipeline.py`

```python
"""Tests for ChEMBL document pipeline."""

import pytest
import pandas as pd
from unittest.mock import MagicMock, patch

from bioetl.application.pipelines.chembl.base import ChemblPipelineBase
from bioetl.domain.configs import PipelineConfig


@pytest.fixture
def document_config():
    """Create test configuration for document pipeline."""
    return {
        "id": "chembl.document",
        "provider": "chembl",
        "entity": "document",
        # ... минимальная конфигурация для тестов
    }


@pytest.mark.unit
def test_document_pipeline_extract(document_config, mock_extraction_service):
    """Test document extraction returns expected structure."""
    # Arrange
    mock_extraction_service.iter_extract.return_value = iter([
        [{"document_chembl_id": "CHEMBL_DOC_1", "title": "Test"}]
    ])

    # Act & Assert
    # ...


@pytest.mark.unit
def test_document_pipeline_transform(document_config):
    """Test document transformation normalizes fields correctly."""
    # ...


@pytest.mark.integration
def test_document_pipeline_end_to_end():
    """Integration test for full document pipeline execution."""
    # ...
```

### Шаг 6: Создание входных данных

**Файл:** `data/input/document.csv`

```csv
document_chembl_id
CHEMBL1121359
CHEMBL1123599
CHEMBL1127448
```

### Шаг 7: Запуск пайплайна

```bash
# Запуск через CLI
python -m bioetl run --pipeline chembl.document --output ./data/output/chembl/document

# С ограничением количества записей
python -m bioetl run --pipeline chembl.document --limit 100

# Dry run (без записи)
python -m bioetl run --pipeline chembl.document --dry-run
```

---

## Часть 2: Добавление нового провайдера (PubChem)

### Обзор задачи

Добавление нового провайдера требует изменений во всех слоях архитектуры:

```
1. Domain Layer     → ProviderId, Config models, Ports
2. Infrastructure   → HTTP Client, Extraction Service, Provider registration
3. Application      → Pipeline, Factory, Mappers
4. Configs          → providers.yaml, pipeline configs
```

### Шаг 1: Обновление Domain Layer

#### 1.1 Добавление ProviderId

**Файл:** `src/bioetl/domain/providers.py`

```python
class ProviderId(str, Enum):
    """Canonical provider identifiers."""

    CHEMBL = "chembl"
    PUBCHEM = "pubchem"  # <-- Уже добавлен, проверить наличие
    UNIPROT = "uniprot"
    PUBMED = "pubmed"
    DUMMY = "dummy"
```

#### 1.2 Создание конфигурационной модели провайдера

**Файл:** `src/bioetl/domain/configs/pipeline.py`

Добавить новый класс конфигурации:

```python
class PubchemSourceConfig(BaseProviderConfig):
    """PubChem source configuration."""

    provider: Literal["pubchem"] = "pubchem"

    # PubChem-специфичные параметры
    api_version: str | None = None
    record_type: Literal["2d", "3d"] = "2d"
    output_format: Literal["JSON", "XML", "SDF"] = "JSON"
    batch_size: PositiveInt | None = 100

    # PUG REST API специфика
    operation: Literal["property", "record", "synonyms"] = "property"
    properties: list[str] | None = None

    model_config = ConfigDict(extra="forbid")

    def resolve_effective_batch_size(
        self, limit: int | None = None, hard_cap: int | None = 100
    ) -> int:
        """Compute effective batch size with constraints."""
        effective_batch = self.batch_size or hard_cap or 100
        if hard_cap is not None:
            effective_batch = min(effective_batch, hard_cap)
        if limit is not None:
            effective_batch = min(effective_batch, limit)
        return effective_batch
```

Обновить Union тип:

```python
ProviderConfigUnion = Annotated[
    ChemblSourceConfig | PubchemSourceConfig | DummyProviderConfig,
    Field(discriminator="provider"),
]
```

Обновить валидатор в `BaseProviderConfig`:

```python
@field_validator("provider")
@classmethod
def validate_provider_known(cls, value: str) -> str:
    """Ensure provider identifier is known to the registry."""
    from bioetl.domain.providers import ProviderId
    known = {provider.value for provider in ProviderId}
    if value not in known:
        raise ValueError(f"Unknown provider: {value}")
    return value
```

### Шаг 2: Создание Infrastructure Layer

#### 2.1 Структура директории

```
src/bioetl/infrastructure/clients/pubchem/
├── __init__.py
├── provider.py                 # Регистрация провайдера
├── factories.py                # Фабрики клиента и сервисов
├── constants.py                # Константы, endpoints
├── request_builder.py          # Построитель URL запросов
├── response_parser.py          # Парсер ответов API
├── paginator.py                # Логика пагинации
└── impl/
    ├── __init__.py
    ├── pubchem_http_client_impl.py
    └── pubchem_extraction_service_impl.py
```

#### 2.2 Константы и маппинги

**Файл:** `src/bioetl/infrastructure/clients/pubchem/constants.py`

```python
"""PubChem API constants and endpoint mappings."""

# PubChem PUG REST API base URL
PUBCHEM_BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

# Entity to endpoint mapping
ENTITY_TO_ENDPOINT: dict[str, str] = {
    "compound": "compound",
    "substance": "substance",
    "assay": "assay",
    "gene": "gene",
    "protein": "protein",
    "pathway": "pathway",
    "taxonomy": "taxonomy",
}

# Input types supported by PubChem
INPUT_TYPES = {
    "cid": "cid",           # Compound ID
    "sid": "sid",           # Substance ID
    "aid": "aid",           # Assay ID
    "name": "name",         # Chemical name
    "smiles": "smiles",     # SMILES string
    "inchi": "inchi",       # InChI string
    "inchikey": "inchikey", # InChI Key
    "formula": "formula",   # Molecular formula
}

# Default properties to fetch for compounds
DEFAULT_COMPOUND_PROPERTIES = [
    "MolecularFormula",
    "MolecularWeight",
    "CanonicalSMILES",
    "IsomericSMILES",
    "InChI",
    "InChIKey",
    "IUPACName",
    "XLogP",
    "ExactMass",
    "MonoisotopicMass",
    "TPSA",
    "Complexity",
    "Charge",
    "HBondDonorCount",
    "HBondAcceptorCount",
    "RotatableBondCount",
    "HeavyAtomCount",
    "AtomStereoCount",
    "DefinedAtomStereoCount",
    "UndefinedAtomStereoCount",
    "BondStereoCount",
    "CovalentUnitCount",
]

# Rate limits
PUBCHEM_RATE_LIMIT_PER_SEC = 5.0  # PubChem рекомендует не более 5 запросов/сек
PUBCHEM_BATCH_SIZE_LIMIT = 100    # Максимум CID в одном запросе


def resolve_endpoint(entity: str) -> str:
    """Resolve entity name to PubChem API endpoint."""
    endpoint = ENTITY_TO_ENDPOINT.get(entity.lower())
    if endpoint is None:
        raise ValueError(
            f"Unknown PubChem entity: {entity}. "
            f"Supported: {list(ENTITY_TO_ENDPOINT.keys())}"
        )
    return endpoint
```

#### 2.3 Request Builder

**Файл:** `src/bioetl/infrastructure/clients/pubchem/request_builder.py`

```python
"""PubChem request URL builder."""

from __future__ import annotations

from urllib.parse import urlencode, urljoin

from bioetl.domain.clients.contracts import RequestBuilderABC
from bioetl.infrastructure.clients.pubchem.constants import (
    DEFAULT_COMPOUND_PROPERTIES,
    PUBCHEM_BASE_URL,
)


class PubchemRequestBuilderImpl(RequestBuilderABC):
    """Builder for PubChem PUG REST API URLs.

    PubChem URL format:
    https://pubchem.ncbi.nlm.nih.gov/rest/pug/<domain>/<input>/<operation>/<output>

    Examples:
    - /compound/cid/2244/property/MolecularWeight/JSON
    - /compound/cid/2244,3672/property/MolecularFormula,MolecularWeight/JSON
    """

    def __init__(
        self,
        base_url: str = PUBCHEM_BASE_URL,
        output_format: str = "JSON",
        max_url_length: int | None = 2000,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._output_format = output_format
        self._max_url_length = max_url_length
        self._current_domain: str | None = None
        self._current_input_type: str = "cid"

    def build_for_endpoint(self, endpoint: str) -> "PubchemRequestBuilderImpl":
        """Set the domain/entity for URL building."""
        self._current_domain = endpoint
        return self

    def build_request(self, filters: dict[str, object]) -> str:
        """Build complete PubChem API URL.

        Args:
            filters: Dictionary with keys:
                - ids: List of IDs or comma-separated string
                - input_type: Type of input (cid, sid, name, smiles, etc.)
                - operation: API operation (property, record, synonyms)
                - properties: List of properties to fetch (for property operation)

        Returns:
            Complete URL string.
        """
        if self._current_domain is None:
            raise ValueError("Domain not set. Call build_for_endpoint() first.")

        # Extract parameters
        ids = filters.get("ids", filters.get("cid", []))
        if isinstance(ids, list):
            ids_str = ",".join(str(i) for i in ids)
        else:
            ids_str = str(ids)

        input_type = str(filters.get("input_type", self._current_input_type))
        operation = str(filters.get("operation", "property"))

        # Handle properties
        properties = filters.get("properties", DEFAULT_COMPOUND_PROPERTIES)
        if isinstance(properties, list):
            properties_str = ",".join(properties)
        else:
            properties_str = str(properties)

        # Build URL path
        # Format: /domain/input_type/ids/operation/properties/format
        if operation == "property":
            path = f"/{self._current_domain}/{input_type}/{ids_str}/{operation}/{properties_str}/{self._output_format}"
        elif operation == "record":
            path = f"/{self._current_domain}/{input_type}/{ids_str}/{self._output_format}"
        else:
            path = f"/{self._current_domain}/{input_type}/{ids_str}/{operation}/{self._output_format}"

        url = f"{self._base_url}{path}"

        # Validate URL length
        if self._max_url_length and len(url) > self._max_url_length:
            raise ValueError(
                f"URL length {len(url)} exceeds maximum {self._max_url_length}"
            )

        return url

    def build_batch_urls(
        self,
        ids: list[str],
        batch_size: int = 100,
        **filters: object,
    ) -> list[str]:
        """Build multiple URLs for batched ID requests."""
        urls = []
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i : i + batch_size]
            batch_filters = {**filters, "ids": batch_ids}
            urls.append(self.build_request(batch_filters))
        return urls


__all__ = ["PubchemRequestBuilderImpl"]
```

#### 2.4 Response Parser

**Файл:** `src/bioetl/infrastructure/clients/pubchem/response_parser.py`

```python
"""PubChem API response parser."""

from __future__ import annotations

from typing import Any

from bioetl.domain.data import RecordBatch
from bioetl.domain.ports.parsing import ResponseParserPortABC


class PubchemResponseParser(ResponseParserPortABC):
    """Parser for PubChem PUG REST API responses.

    PubChem returns different structures based on operation:

    Property response:
    {
        "PropertyTable": {
            "Properties": [
                {"CID": 2244, "MolecularWeight": 180.16, ...},
                {"CID": 3672, "MolecularWeight": 206.29, ...}
            ]
        }
    }

    Record response (JSON):
    {
        "PC_Compounds": [
            {"id": {"id": {"cid": 2244}}, "atoms": {...}, ...}
        ]
    }
    """

    def parse_to_records(self, response: dict[str, Any]) -> RecordBatch:
        """Parse PubChem response into list of record dicts."""
        if not response:
            return []

        # Handle Property response
        if "PropertyTable" in response:
            properties = response.get("PropertyTable", {}).get("Properties", [])
            return self._normalize_property_records(properties)

        # Handle Record response
        if "PC_Compounds" in response:
            compounds = response.get("PC_Compounds", [])
            return self._normalize_compound_records(compounds)

        # Handle Substance response
        if "PC_Substances" in response:
            substances = response.get("PC_Substances", [])
            return self._normalize_substance_records(substances)

        # Handle direct list response
        if isinstance(response, list):
            return response

        # Unknown format - return as single record
        return [response]

    def _normalize_property_records(
        self, properties: list[dict[str, Any]]
    ) -> RecordBatch:
        """Normalize property table records."""
        records = []
        for prop in properties:
            record = {}
            for key, value in prop.items():
                # Convert PascalCase to snake_case for consistency
                snake_key = self._to_snake_case(key)
                record[snake_key] = value
            records.append(record)
        return records

    def _normalize_compound_records(
        self, compounds: list[dict[str, Any]]
    ) -> RecordBatch:
        """Normalize PC_Compounds records to flat structure."""
        records = []
        for compound in compounds:
            record = {}

            # Extract CID
            cid_path = compound.get("id", {}).get("id", {})
            if isinstance(cid_path, dict):
                record["cid"] = cid_path.get("cid")

            # Extract properties
            if "props" in compound:
                for prop in compound["props"]:
                    label = prop.get("urn", {}).get("label", "")
                    name = prop.get("urn", {}).get("name", "")
                    key = f"{label}_{name}".lower().replace(" ", "_")

                    # Get value from appropriate field
                    value_obj = prop.get("value", {})
                    value = (
                        value_obj.get("sval") or
                        value_obj.get("ival") or
                        value_obj.get("fval") or
                        value_obj.get("binary")
                    )
                    record[key] = value

            records.append(record)
        return records

    def _normalize_substance_records(
        self, substances: list[dict[str, Any]]
    ) -> RecordBatch:
        """Normalize PC_Substances records."""
        records = []
        for substance in substances:
            record = {}
            sid_path = substance.get("sid", {}).get("id")
            record["sid"] = sid_path
            # Add more fields as needed
            records.append(record)
        return records

    @staticmethod
    def _to_snake_case(name: str) -> str:
        """Convert PascalCase/camelCase to snake_case."""
        import re
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


__all__ = ["PubchemResponseParser"]
```

#### 2.5 HTTP Client Implementation

**Файл:** `src/bioetl/infrastructure/clients/pubchem/impl/pubchem_http_client_impl.py`

```python
"""PubChem HTTP client implementation."""

from __future__ import annotations

from typing import Any, Iterator

from bioetl.domain.clients.contracts import (
    DataClientABC,
    DataClientWithBuilderProtocol,
    RequestBuilderABC,
)
from bioetl.domain.observability.contracts import LoggingPortABC
from bioetl.domain.ports.parsing import ResponseParserPortABC
from bioetl.domain.types import ApiPayload
from bioetl.infrastructure.clients.base.rate_limiter import RateLimiterABC


class PubchemHttpClientImpl(DataClientABC, DataClientWithBuilderProtocol):
    """HTTP client for PubChem PUG REST API."""

    def __init__(
        self,
        request_builder: RequestBuilderABC,
        response_parser: ResponseParserPortABC,
        rate_limiter: RateLimiterABC,
        http_client: Any,  # UnifiedHttpClient
        logger: LoggingPortABC,
        provider: str = "pubchem",
        error_handler: Any | None = None,
    ) -> None:
        self._request_builder = request_builder
        self._response_parser = response_parser
        self._rate_limiter = rate_limiter
        self._http_client = http_client
        self._logger = logger
        self._provider = provider
        self._error_handler = error_handler

    @property
    def request_builder(self) -> RequestBuilderABC:
        """Return the request builder for URL construction."""
        return self._request_builder

    def metadata(self) -> dict[str, Any]:
        """Return PubChem service metadata.

        Note: PubChem doesn't have a dedicated metadata endpoint like ChEMBL.
        Returns static version info.
        """
        return {
            "provider": "pubchem",
            "api_version": "pug_rest_v1",
            "base_url": "https://pubchem.ncbi.nlm.nih.gov/rest/pug",
        }

    def fetch(self, entity: str, **filters: Any) -> dict[str, Any]:
        """Fetch data from PubChem API.

        Args:
            entity: Entity type (compound, substance, assay).
            **filters: Query filters including ids, properties, etc.

        Returns:
            API response as dictionary.
        """
        self._rate_limiter.acquire()

        url = (
            self._request_builder
            .build_for_endpoint(entity)
            .build_request(filters)
        )

        self._logger.debug(
            "pubchem_fetch",
            entity=entity,
            url=url,
        )

        try:
            response = self._http_client.get(url)
            return response.json() if hasattr(response, "json") else response
        except Exception as exc:
            self._logger.error(
                "pubchem_fetch_error",
                entity=entity,
                error=str(exc),
            )
            if self._error_handler:
                return self._error_handler.handle(exc, url)
            raise

    def iter_pages(self, request: str) -> Iterator[ApiPayload]:
        """Iterate over paginated results.

        Note: PubChem uses list-based batching rather than offset pagination.
        For large requests, split IDs into batches and make separate calls.
        """
        self._rate_limiter.acquire()

        try:
            response = self._http_client.get(request)
            data = response.json() if hasattr(response, "json") else response
            yield data
        except Exception as exc:
            self._logger.error(
                "pubchem_iter_pages_error",
                url=request,
                error=str(exc),
            )
            raise


__all__ = ["PubchemHttpClientImpl"]
```

#### 2.6 Extraction Service Implementation

**Файл:** `src/bioetl/infrastructure/clients/pubchem/impl/pubchem_extraction_service_impl.py`

```python
"""PubChem extraction service implementation."""

from __future__ import annotations

from typing import Any, Iterable

from bioetl.domain.clients.contracts import DataClientWithBuilderProtocol
from bioetl.domain.data import RecordBatch
from bioetl.domain.observability.contracts import LoggingPortABC
from bioetl.domain.ports.extraction import ExtractionServiceABC
from bioetl.domain.ports.filters import FilterEnricherABC
from bioetl.infrastructure.clients.pubchem.constants import (
    DEFAULT_COMPOUND_PROPERTIES,
    PUBCHEM_BATCH_SIZE_LIMIT,
    resolve_endpoint,
)
from bioetl.infrastructure.clients.pubchem.response_parser import PubchemResponseParser


class PubchemExtractionServiceImpl(ExtractionServiceABC):
    """Extraction service for PubChem data.

    Returns raw dicts - domain model mapping is application layer responsibility.
    """

    def __init__(
        self,
        client: DataClientWithBuilderProtocol,
        logger: LoggingPortABC,
        batch_size: int = PUBCHEM_BATCH_SIZE_LIMIT,
        filter_enricher: FilterEnricherABC | None = None,
        parser: PubchemResponseParser | None = None,
    ) -> None:
        self._client = client
        self._batch_size = min(batch_size, PUBCHEM_BATCH_SIZE_LIMIT)
        self._logger = logger
        self._filter_enricher = filter_enricher
        self._parser = parser or PubchemResponseParser()

    @property
    def client(self) -> DataClientWithBuilderProtocol:
        """Return the underlying data client."""
        return self._client

    @property
    def batch_size(self) -> int:
        """Return the default batch size."""
        return self._batch_size

    def get_release_version(self) -> str:
        """Get PubChem version identifier.

        Note: PubChem doesn't expose version like ChEMBL.
        Returns current date-based version.
        """
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d")

    def extract_all(self, entity: str, **filters: object) -> RecordBatch:
        """Extract all records for an entity as raw dicts."""
        records: RecordBatch = []
        for batch in self.iter_extract(entity, **filters):
            records.extend(batch)
        return records

    def iter_extract(
        self,
        entity: str,
        *,
        chunk_size: int | None = None,
        **filters: object,
    ) -> Iterable[RecordBatch]:
        """Stream records from PubChem as raw dicts.

        Args:
            entity: Entity name to extract (compound, substance, assay).
            chunk_size: Records per batch.
            **filters: Additional query filters including:
                - ids/cid/sid: List of IDs to fetch
                - properties: List of properties (for compounds)
                - operation: API operation type

        Yields:
            RecordBatch: Batches of raw record dictionaries.
        """
        effective_chunk_size = min(
            chunk_size or self._batch_size,
            PUBCHEM_BATCH_SIZE_LIMIT,
        )

        # Get IDs from filters
        ids = filters.pop("ids", filters.pop("cid", filters.pop("sid", [])))
        if isinstance(ids, str):
            ids = [i.strip() for i in ids.split(",")]

        if not ids:
            self._logger.warning(
                "pubchem_no_ids",
                entity=entity,
                message="No IDs provided for extraction",
            )
            return

        # Enrich filters if enricher available
        if self._filter_enricher:
            filters = self._filter_enricher.enrich_filters(entity, dict(filters))

        # Resolve endpoint
        endpoint = resolve_endpoint(entity)

        # Process in batches
        for i in range(0, len(ids), effective_chunk_size):
            batch_ids = ids[i : i + effective_chunk_size]

            self._logger.debug(
                "pubchem_batch_extract",
                entity=entity,
                batch_start=i,
                batch_size=len(batch_ids),
            )

            # Build and execute request
            batch_filters = {**filters, "ids": batch_ids}

            url = (
                self._client.request_builder
                .build_for_endpoint(endpoint)
                .build_request(batch_filters)
            )

            for page_data in self._client.iter_pages(url):
                records = self._parser.parse_to_records(page_data)
                if records:
                    yield records

    def request_batch(
        self,
        entity: str,
        batch_ids: list[str],
        filter_key: str,
    ) -> dict[str, Any]:
        """Request a batch of records by IDs.

        Args:
            entity: Entity name.
            batch_ids: List of IDs.
            filter_key: Filter parameter key (cid, sid, etc.).

        Returns:
            Raw API response.
        """
        return self._client.fetch(
            entity,
            ids=batch_ids,
            input_type=filter_key,
        )

    def parse_response(self, raw_response: object) -> RecordBatch:
        """Parse raw response into record dicts."""
        if raw_response is None:
            return []
        if not isinstance(raw_response, dict):
            return []
        return self._parser.parse_to_records(raw_response)

    def serialize_records(self, entity: str, records: RecordBatch) -> RecordBatch:
        """Serialize records for storage."""
        return records


__all__ = ["PubchemExtractionServiceImpl"]
```

#### 2.7 Provider Registration

**Файл:** `src/bioetl/infrastructure/clients/pubchem/provider.py`

```python
"""PubChem provider components and registration."""

from __future__ import annotations

from typing import Any

from bioetl.domain.clients.contracts import DataClientABC
from bioetl.domain.configs import HttpClientConfig, PubchemSourceConfig
from bioetl.domain.ports.extraction import ExtractionServiceABC
from bioetl.domain.ports.filters import FilterEnricherABC
from bioetl.domain.providers import ProviderComponents, ProviderDefinition, ProviderId
from bioetl.domain.transform.contracts import (
    NormalizationConfigProviderProtocol,
    NormalizationServiceABC,
)
from bioetl.infrastructure.transform.factories import create_normalization_service


class PubchemProviderComponentsFactory(
    ProviderComponents[
        DataClientABC,
        ExtractionServiceABC,
        NormalizationServiceABC,
        object,
    ]
):
    """Factory set for building PubChem provider components."""

    def create_client(self, config: PubchemSourceConfig) -> DataClientABC:
        """Build configured PubChem data client."""
        from bioetl.infrastructure.clients.pubchem.factories import (
            create_pubchem_client,
        )
        # Note: Logger and metrics will be injected by the factory
        # This is a simplified version - full implementation needs DI
        raise NotImplementedError(
            "Use create_pubchem_client() factory with explicit dependencies"
        )

    def create_extraction_service(
        self,
        config: PubchemSourceConfig,
        *,
        client: DataClientABC | None = None,
        filter_enricher: FilterEnricherABC | None = None,
        logger: Any | None = None,
        metrics: Any | None = None,
    ) -> ExtractionServiceABC:
        """Construct extraction service with optional prebuilt client."""
        from bioetl.infrastructure.clients.pubchem.factories import (
            create_pubchem_extraction_service,
        )
        return create_pubchem_extraction_service(
            config,
            logger=logger,
            metrics=metrics,
            client=client,
            filter_enricher=filter_enricher,
        )

    def create_normalization_service(
        self,
        config: PubchemSourceConfig,
        *,
        client: DataClientABC | None = None,
        pipeline_config: NormalizationConfigProviderProtocol | None = None,
    ) -> NormalizationServiceABC:
        """Create normalization service using pipeline configuration."""
        _ = client
        if pipeline_config is None:
            raise ValueError(
                "NormalizationConfigProviderProtocol is required to build "
                "normalization service"
            )
        return create_normalization_service(pipeline_config)

    def create_entity_model_registry(self) -> Any:
        """Create provider-specific entity model registry."""
        # PubChem может использовать общий реестр или специфичный
        return None  # или создать PubchemModelRegistry

    def create_writer(
        self,
        config: PubchemSourceConfig,
        *,
        client: DataClientABC | None = None,
    ) -> object:
        """Create provider-specific writer (not implemented for PubChem)."""
        raise NotImplementedError("PubChem writer not implemented")


def register_pubchem_provider(
    http: HttpClientConfig | None = None,
) -> ProviderDefinition:
    """Create PubChem provider definition."""
    return ProviderDefinition(
        id=ProviderId.PUBCHEM,
        config_type=PubchemSourceConfig,
        components=PubchemProviderComponentsFactory(),
        description="PubChem data provider (NCBI)",
        http=http,
    )


__all__ = [
    "PubchemProviderComponentsFactory",
    "register_pubchem_provider",
]
```

#### 2.8 Factories

**Файл:** `src/bioetl/infrastructure/clients/pubchem/factories.py`

```python
"""Factories for PubChem clients."""

from typing import Any

from bioetl.domain.clients.contracts import DataClientABC
from bioetl.domain.configs import HttpClientConfig, PubchemSourceConfig
from bioetl.domain.observability.contracts import LoggingPortABC, MetricsPortABC
from bioetl.domain.ports.extraction import ExtractionServiceABC
from bioetl.domain.ports.filters import FilterEnricherABC
from bioetl.infrastructure.clients.base.factories import (
    build_http_client,
    build_rate_limiter,
)
from bioetl.infrastructure.clients.base.http_error_handler import (
    DefaultHttpErrorHandler,
)
from bioetl.infrastructure.clients.pubchem.constants import PUBCHEM_BASE_URL
from bioetl.infrastructure.clients.pubchem.impl.pubchem_extraction_service_impl import (
    PubchemExtractionServiceImpl,
)
from bioetl.infrastructure.clients.pubchem.impl.pubchem_http_client_impl import (
    PubchemHttpClientImpl,
)
from bioetl.infrastructure.clients.pubchem.request_builder import (
    PubchemRequestBuilderImpl,
)
from bioetl.infrastructure.clients.pubchem.response_parser import PubchemResponseParser


def create_pubchem_client(
    source_config: PubchemSourceConfig,
    logger: LoggingPortABC,
    metrics: MetricsPortABC,
    http_config: HttpClientConfig | None = None,
    **options: Any,
) -> DataClientABC:
    """Create a new PubChem client with explicit dependencies.

    Args:
        source_config: Source configuration.
        logger: Required logger instance.
        metrics: Required metrics instance.
        http_config: Optional HTTP configuration.
        **options: Additional options (base_url, output_format).

    Returns:
        Configured PubChem client instance.
    """
    resolved_config = http_config or source_config.http

    # Create unified HTTP client
    unified_client = build_http_client(
        provider="pubchem",
        logger=logger,
        metrics=metrics,
        config=resolved_config,
    )

    # Allow explicit overrides
    base_url = str(options.get("base_url", source_config.base_url))
    output_format = str(options.get("output_format", source_config.output_format))

    # Rate limiter
    rate_limiter = build_rate_limiter(logger, config=resolved_config)

    # Error handler
    error_handler = DefaultHttpErrorHandler(logger)

    return PubchemHttpClientImpl(
        request_builder=PubchemRequestBuilderImpl(
            base_url=base_url,
            output_format=output_format,
        ),
        response_parser=PubchemResponseParser(),
        rate_limiter=rate_limiter,
        http_client=unified_client,
        logger=logger,
        provider="pubchem",
        error_handler=error_handler,
    )


def create_pubchem_extraction_service(
    config: PubchemSourceConfig,
    logger: LoggingPortABC,
    metrics: MetricsPortABC,
    http_config: HttpClientConfig | None = None,
    *,
    client: DataClientABC | None = None,
    filter_enricher: FilterEnricherABC | None = None,
) -> ExtractionServiceABC:
    """Create a new PubChem extraction service.

    Args:
        config: Source configuration.
        logger: Required logger instance.
        metrics: Required metrics instance.
        http_config: Optional HTTP configuration.
        client: Optional pre-created client.
        filter_enricher: Optional filter enricher.

    Returns:
        Configured extraction service.
    """
    if client is None:
        client = create_pubchem_client(
            config,
            logger=logger,
            metrics=metrics,
            http_config=http_config,
        )

    return PubchemExtractionServiceImpl(
        client=client,
        logger=logger,
        batch_size=config.resolve_effective_batch_size(hard_cap=100),
        filter_enricher=filter_enricher,
        parser=PubchemResponseParser(),
    )


__all__ = [
    "create_pubchem_client",
    "create_pubchem_extraction_service",
]
```

#### 2.9 Module Init

**Файл:** `src/bioetl/infrastructure/clients/pubchem/__init__.py`

```python
"""PubChem client infrastructure."""

from bioetl.infrastructure.clients.pubchem.factories import (
    create_pubchem_client,
    create_pubchem_extraction_service,
)
from bioetl.infrastructure.clients.pubchem.provider import (
    PubchemProviderComponentsFactory,
    register_pubchem_provider,
)

__all__ = [
    "create_pubchem_client",
    "create_pubchem_extraction_service",
    "PubchemProviderComponentsFactory",
    "register_pubchem_provider",
]
```

### Шаг 3: Создание Application Layer

#### 3.1 Pipeline Base

**Файл:** `src/bioetl/application/pipelines/pubchem/base.py`

```python
"""Base pipeline implementation for PubChem data extraction."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from bioetl.application.pipelines.base import PipelineBase
from bioetl.application.pipelines.stages.extract import ExtractStage
from bioetl.domain.clients.base.output.contracts import (
    RunMetadataBuilderProtocol,
    WriteResult,
)
from bioetl.domain.configs import PipelineConfig
from bioetl.domain.models import RunContext
from bioetl.domain.observability import LoggingPortABC
from bioetl.domain.pipelines.contracts import ErrorPolicyABC, LoaderABC, PipelineHookABC
from bioetl.domain.ports.extraction import ExtractionServiceABC
from bioetl.domain.record_source import RecordSourceABC
from bioetl.domain.schemas.pipeline_contracts import (
    PipelineSchemaModel,
    get_pipeline_contract,
)
from bioetl.domain.transform.contracts import (
    HashServiceABC,
    IndexGeneratorABC,
    NormalizationServiceABC,
    TimestampProviderABC,
)
from bioetl.domain.transform.transformers import TransformerABC
from bioetl.domain.validation.service import ValidationService


class PubchemPipelineBase(PipelineBase):
    """Base class for PubChem pipelines."""

    def __init__(
        self,
        config: PipelineConfig,
        logger: LoggingPortABC,
        validation_service: ValidationService,
        extraction_service: ExtractionServiceABC,
        hash_service: HashServiceABC,
        index_generator: IndexGeneratorABC,
        timestamp_provider: TimestampProviderABC,
        schema_contract: PipelineSchemaModel | None = None,
        loader: LoaderABC | None = None,
        metadata_builder: RunMetadataBuilderProtocol | None = None,
        normalization_service: NormalizationServiceABC | None = None,
        hooks: list[PipelineHookABC] | None = None,
        error_policy: ErrorPolicyABC | None = None,
        transformer: TransformerABC | None = None,
        post_transformer: TransformerABC | None = None,
        record_source: RecordSourceABC | None = None,
    ) -> None:
        self._extraction_service = extraction_service
        self._pubchem_version: str | None = None

        if normalization_service is None:
            raise ValueError("Normalization service is required.")

        if loader is None:
            raise ValueError("Loader must be provided.")

        # Create extractor
        extractor = ExtractStage(
            extraction_service=extraction_service,
            record_mapper=None,  # PubChem uses generic mapper
            entity=config.entity_name,
            record_source=record_source,
        )

        # Resolve schema contract
        resolved_contract = schema_contract or get_pipeline_contract(
            config.id, default_entity=config.entity_name
        )

        super().__init__(
            config=config,
            logger=logger,
            validation_service=validation_service,
            loader=loader,
            hash_service=hash_service,
            index_generator=index_generator,
            timestamp_provider=timestamp_provider,
            schema_contract=resolved_contract,
            metadata_builder=metadata_builder,
            extractor=extractor,
            hooks=hooks,
            error_policy=error_policy,
            transformer=transformer,
            post_transformer=post_transformer,
        )

        self._loader = loader
        self._extractor = extractor
        self._normalization_service = normalization_service

    def get_version(self) -> str:
        """Return PubChem version (date-based)."""
        if self._pubchem_version is not None:
            return self._pubchem_version

        try:
            self._pubchem_version = self._extraction_service.get_release_version()
        except Exception as exc:
            self._logger.warning(
                "Failed to get PubChem version",
                error=str(exc),
            )
            self._pubchem_version = "unknown"

        return self._pubchem_version

    def _enrich_context(self, context: RunContext) -> None:
        """Adds PubChem version to metadata."""
        context.metadata["pubchem_version"] = self.get_version()

    def extract(self, **kwargs: Any) -> pd.DataFrame:
        """Extract data from PubChem."""
        if self._extractor is None:
            raise RuntimeError("Extractor not initialized.")

        extract_result = self._extractor.extract(**kwargs)

        if extract_result is None:
            return pd.DataFrame()

        if isinstance(extract_result, pd.DataFrame):
            return extract_result

        chunks = []
        for chunk in extract_result:
            if chunk is not None and not chunk.empty:
                chunks.append(chunk)

        if not chunks:
            return pd.DataFrame()

        return pd.concat(chunks, ignore_index=True, copy=False)

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform PubChem data."""
        if self._normalization_service:
            df = self._normalization_service.normalize(df)
        return df

    def write(
        self,
        df: pd.DataFrame,
        output_path: Path,
        context: RunContext,
    ) -> WriteResult:
        """Persist transformed data."""
        return self._write_with_loader(df, output_path, context)


__all__ = ["PubchemPipelineBase"]
```

#### 3.2 Pipeline Factory

**Файл:** `src/bioetl/application/pipelines/pubchem/factories.py`

```python
"""Factory for PubChem pipeline creation."""

from __future__ import annotations

from bioetl.application.contracts import PipelineContainerABC, PipelineFactoryABC
from bioetl.application.pipelines.base import PipelineBase
from bioetl.application.pipelines.pubchem.base import PubchemPipelineBase


class PubchemPipelineFactory(PipelineFactoryABC):
    """Factory for creating PubChem entity pipelines."""

    def create(
        self,
        container: PipelineContainerABC,
        *,
        limit: int | None = None,
    ) -> PipelineBase:
        """Create a fully configured PubChem pipeline.

        Args:
            container: Dependency injection container.
            limit: Optional record limit.

        Returns:
            Configured PubchemPipelineBase ready to run.
        """
        logger = container.get_logger()
        extraction_service = container.get_extraction_service()
        record_source = container.get_record_source(
            extraction_service=extraction_service,
            limit=limit,
            logger=logger,
        )

        pipeline: PipelineBase = PubchemPipelineBase(
            config=container.config,
            logger=logger,
            validation_service=container.get_validation_service(),
            loader=container.get_loader(),
            extraction_service=extraction_service,
            hash_service=container.get_hash_service(),
            index_generator=container.get_index_generator(),
            timestamp_provider=container.get_timestamp_provider(),
            schema_contract=container.get_schema_contract(),
            metadata_builder=container.get_metadata_builder(),
            normalization_service=container.get_normalization_service(),
            hooks=container.get_hooks(),
            error_policy=container.get_error_policy(),
            record_source=record_source,
        )

        # Set post-transformer
        pipeline.set_post_transformer(
            container.get_post_transformer(version_provider=pipeline.get_version)
        )

        # Register hooks and error policy
        pipeline.register_hooks(container.get_hooks())
        pipeline.set_error_policy(container.get_error_policy())

        return pipeline


__all__ = ["PubchemPipelineFactory"]
```

### Шаг 4: Обновление конфигураций

#### 4.1 Регистрация провайдера

**Файл:** `configs/providers.yaml`

```yaml
providers:
  - id: chembl
    module: bioetl.infrastructure.clients.chembl.provider
    factory: register_chembl_provider
    active: true
    description: "ChEMBL data provider"
    http_client:
      base_url: https://www.ebi.ac.uk/chembl/api/data
      timeout: 30
      retries: 3
      backoff: 2.0
      rate_limit: 10.0

  - id: pubchem
    module: bioetl.infrastructure.clients.pubchem.provider
    factory: register_pubchem_provider
    active: true
    description: "PubChem data provider (NCBI)"
    http_client:
      base_url: https://pubchem.ncbi.nlm.nih.gov/rest/pug
      timeout: 60
      retries: 3
      backoff: 2.0
      rate_limit: 5.0
```

#### 4.2 Создание pipeline config

**Файл:** `configs/pipelines/pubchem/compound.yaml`

```yaml
# PubChem Compound Pipeline Configuration

id: pubchem.compound
provider: pubchem
entity: compound
primary_key: cid

input_mode: id_only
input_path: data/input/pubchem_compounds.csv
output_path: ./data/output/pubchem/compound
batch_size: 100

provider_config:
  provider: pubchem
  base_url: https://pubchem.ncbi.nlm.nih.gov/rest/pug
  client:
    timeout_sec: 60.0
    max_retries: 3
    rate_limit_per_sec: 5.0
  batch_size: 100
  record_type: "2d"
  output_format: "JSON"
  operation: "property"
  properties:
    - MolecularFormula
    - MolecularWeight
    - CanonicalSMILES
    - IsomericSMILES
    - InChI
    - InChIKey
    - IUPACName
    - XLogP
    - TPSA
    - HBondDonorCount
    - HBondAcceptorCount

csv_options:
  delimiter: ","
  header: true

pipeline:
  name: compound_pubchem
  version: "1.0.0"
  owner: "Data Acquisition Team"
  description: "Extract compound properties from PubChem"

transform:
  serialization_mode: pipe

fields:
  - name: cid
    data_type: integer
    is_nullable: false
    is_filterable: true
    description: "PubChem Compound ID"

  - name: molecular_formula
    data_type: string
    is_nullable: true
    is_filterable: false
    description: "Molecular formula"

  - name: molecular_weight
    data_type: number
    is_nullable: true
    is_filterable: true
    description: "Molecular weight"

  - name: canonical_smiles
    data_type: string
    is_nullable: true
    is_filterable: false
    description: "Canonical SMILES"

  - name: isomeric_smiles
    data_type: string
    is_nullable: true
    is_filterable: false
    description: "Isomeric SMILES"

  - name: in_ch_i
    data_type: string
    is_nullable: true
    is_filterable: false
    description: "InChI"

  - name: in_ch_i_key
    data_type: string
    is_nullable: true
    is_filterable: true
    description: "InChI Key"

  - name: iupac_name
    data_type: string
    is_nullable: true
    is_filterable: false
    description: "IUPAC name"

  - name: x_log_p
    data_type: number
    is_nullable: true
    is_filterable: true
    description: "XLogP value"

  - name: tpsa
    data_type: number
    is_nullable: true
    is_filterable: true
    description: "Topological Polar Surface Area"

  - name: h_bond_donor_count
    data_type: integer
    is_nullable: true
    is_filterable: true
    description: "Hydrogen bond donor count"

  - name: h_bond_acceptor_count
    data_type: integer
    is_nullable: true
    is_filterable: true
    description: "Hydrogen bond acceptor count"

quality:
  hashing:
    business_key_fields:
      - cid
  normalization:
    case_sensitive_fields:
      - canonical_smiles
      - isomeric_smiles
      - in_ch_i
    id_fields:
      - cid
      - in_ch_i_key
```

### Шаг 5: Регистрация в реестре пайплайнов

**Файл:** `src/bioetl/application/pipelines/registry.py`

```python
from bioetl.application.pipelines.chembl.factories import ChemblPipelineFactory
from bioetl.application.pipelines.pubchem.factories import PubchemPipelineFactory

_FACTORIES: dict[str, PipelineFactoryABC] = {
    # ChEMBL pipelines
    "chembl.activity": ChemblPipelineFactory(),
    "chembl.assay": ChemblPipelineFactory(),
    "chembl.molecule": ChemblPipelineFactory(),
    "chembl.target": ChemblPipelineFactory(),
    "chembl.document": ChemblPipelineFactory(),

    # PubChem pipelines
    "pubchem.compound": PubchemPipelineFactory(),
    "pubchem.substance": PubchemPipelineFactory(),
    "pubchem.assay": PubchemPipelineFactory(),
}
```

### Шаг 6: Создание тестов

#### 6.1 Unit tests

**Файл:** `tests/bioetl/infrastructure/clients/pubchem/test_provider.py`

```python
"""Tests for PubChem provider."""

import pytest
from unittest.mock import MagicMock

from bioetl.domain.configs import HttpClientConfig, PubchemSourceConfig
from bioetl.infrastructure.clients.pubchem.provider import (
    PubchemProviderComponentsFactory,
    register_pubchem_provider,
)
from bioetl.domain.providers import ProviderId


@pytest.fixture
def pubchem_config() -> PubchemSourceConfig:
    return PubchemSourceConfig(
        base_url="https://pubchem.ncbi.nlm.nih.gov/rest/pug",
        http=HttpClientConfig(
            timeout_sec=60,
            max_retries=3,
            rate_limit_per_sec=5.0,
        ),
    )


def test_register_pubchem_provider():
    """Test provider registration returns correct definition."""
    definition = register_pubchem_provider()

    assert definition.id == ProviderId.PUBCHEM
    assert definition.config_type == PubchemSourceConfig
    assert definition.description == "PubChem data provider (NCBI)"


def test_pubchem_config_batch_size_resolution(pubchem_config):
    """Test batch size resolution respects limits."""
    assert pubchem_config.resolve_effective_batch_size() == 100
    assert pubchem_config.resolve_effective_batch_size(limit=50) == 50
    assert pubchem_config.resolve_effective_batch_size(hard_cap=75) == 75
```

**Файл:** `tests/bioetl/infrastructure/clients/pubchem/test_request_builder.py`

```python
"""Tests for PubChem request builder."""

import pytest

from bioetl.infrastructure.clients.pubchem.request_builder import (
    PubchemRequestBuilderImpl,
)


def test_build_property_request():
    """Test building property request URL."""
    builder = PubchemRequestBuilderImpl()

    url = (
        builder
        .build_for_endpoint("compound")
        .build_request({
            "ids": [2244, 3672],
            "properties": ["MolecularWeight", "CanonicalSMILES"],
        })
    )

    assert "compound" in url
    assert "cid" in url
    assert "2244,3672" in url
    assert "MolecularWeight,CanonicalSMILES" in url
    assert "JSON" in url


def test_build_batch_urls():
    """Test building multiple batch URLs."""
    builder = PubchemRequestBuilderImpl()
    builder.build_for_endpoint("compound")

    ids = [str(i) for i in range(1, 251)]  # 250 IDs
    urls = builder.build_batch_urls(ids, batch_size=100)

    assert len(urls) == 3  # 100 + 100 + 50
```

**Файл:** `tests/bioetl/infrastructure/clients/pubchem/test_response_parser.py`

```python
"""Tests for PubChem response parser."""

import pytest

from bioetl.infrastructure.clients.pubchem.response_parser import (
    PubchemResponseParser,
)


@pytest.fixture
def parser():
    return PubchemResponseParser()


def test_parse_property_response(parser):
    """Test parsing property table response."""
    response = {
        "PropertyTable": {
            "Properties": [
                {"CID": 2244, "MolecularWeight": 180.16, "CanonicalSMILES": "CC(=O)OC1=CC=CC=C1C(=O)O"},
                {"CID": 3672, "MolecularWeight": 206.29, "CanonicalSMILES": "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O"},
            ]
        }
    }

    records = parser.parse_to_records(response)

    assert len(records) == 2
    assert records[0]["cid"] == 2244
    assert records[0]["molecular_weight"] == 180.16
    assert "canonical_smiles" in records[0]


def test_parse_empty_response(parser):
    """Test parsing empty response."""
    assert parser.parse_to_records({}) == []
    assert parser.parse_to_records(None) == []
```

#### 6.2 Integration tests

**Файл:** `tests/integration/test_pubchem_pipeline.py`

```python
"""Integration tests for PubChem pipeline."""

import pytest


@pytest.mark.integration
@pytest.mark.slow
def test_pubchem_compound_extraction():
    """Test extracting compound data from PubChem API."""
    # This test requires network access
    # ...
    pass
```

---

## Часть 3: Чек-лист для добавления нового провайдера

### Domain Layer
- [ ] Добавить `ProviderId` в enum (если еще нет)
- [ ] Создать `<Provider>SourceConfig` класс конфигурации
- [ ] Обновить `ProviderConfigUnion` типа
- [ ] Обновить валидатор провайдеров

### Infrastructure Layer
- [ ] Создать директорию `infrastructure/clients/<provider>/`
- [ ] Реализовать `constants.py` (endpoints, mappings)
- [ ] Реализовать `request_builder.py` (URL building)
- [ ] Реализовать `response_parser.py` (response parsing)
- [ ] Реализовать `impl/<provider>_http_client_impl.py`
- [ ] Реализовать `impl/<provider>_extraction_service_impl.py`
- [ ] Реализовать `provider.py` (registration factory)
- [ ] Реализовать `factories.py` (client/service factories)
- [ ] Создать `__init__.py` с exports

### Application Layer
- [ ] Создать `pipelines/<provider>/base.py`
- [ ] Создать `pipelines/<provider>/factories.py`
- [ ] Создать mappers если нужны
- [ ] Зарегистрировать в `pipelines/registry.py`

### Configuration
- [ ] Добавить в `configs/providers.yaml`
- [ ] Создать `configs/pipelines/<provider>/` директорию
- [ ] Создать pipeline YAML файлы
- [ ] Создать `configs/defaults/<provider>.yaml` (опционально)

### Tests
- [ ] Unit tests для provider components
- [ ] Unit tests для request builder
- [ ] Unit tests для response parser
- [ ] Unit tests для extraction service
- [ ] Integration tests
- [ ] Golden tests (опционально)

### Documentation
- [ ] Обновить README
- [ ] Добавить API документацию
- [ ] Добавить примеры использования

---

## Часть 4: Архитектурные правила

### Зависимости между слоями

```
Interfaces → Application → Infrastructure
                ↓               ↓
              Domain ←──────────┘
```

- **Domain** не зависит ни от чего (чистая бизнес-логика)
- **Infrastructure** зависит только от Domain
- **Application** зависит от Domain и Infrastructure
- **Interfaces** зависит от Application

### Naming Conventions

| Суффикс | Когда использовать | Пример |
|---------|-------------------|--------|
| `*ABC` | Абстрактный базовый класс | `ExtractionServiceABC` |
| `*Impl` | Реализация ABC | `ChemblHttpClientImpl` |
| `*Factory` | Создает объекты | `ChemblPipelineFactory` |
| `*Protocol` | Runtime checkable protocol | `ProviderComponents` |
| `*Config` | Pydantic config model | `ChemblSourceConfig` |
| `*Service` | Stateless business logic | `ValidationService` |

### Тестирование

```bash
# Запуск всех тестов
pytest

# Только unit тесты
pytest -m unit

# Только integration тесты
pytest -m integration

# Проверка coverage (минимум 85%)
pytest --cov=bioetl --cov-fail-under=85

# Проверка архитектурных правил
pytest tests/architecture/
```

---

## Полезные ссылки

- [ChEMBL API Documentation](https://www.ebi.ac.uk/chembl/api/data/docs)
- [PubChem PUG REST API](https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest)
- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
