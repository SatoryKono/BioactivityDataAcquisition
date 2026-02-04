# /new-pipeline

Создание нового ETL-пайплайна для провайдера/сущности в проекте BioETL.

## Использование

```
/new-pipeline [provider] [entity]
```

**Примеры:**
- `/new-pipeline chembl mechanism` — новый пайплайн для ChEMBL mechanism
- `/new-pipeline drugbank drug` — новый провайдер DrugBank с сущностью drug
- `/new-pipeline` — интерактивный режим с вопросами

---

## Инструкции для Claude

При вызове этого skill выполни следующие шаги:

### Шаг 1: Сбор информации

Если аргументы не переданы, запроси у пользователя через AskUserQuestion:

1. **Provider** — выбор из: `chembl`, `pubchem`, `uniprot`, `crossref`, `openalex`, `pubmed`, `semanticscholar`, или новый
2. **Entity type** — snake_case, singular (например: `activity`, `molecule`, `mechanism`)
3. **Primary key** — имя поля первичного ключа (например: `mechanism_id`, `drug_id`)
4. **Business fields** — список полей в формате `name:type:nullable` где type = `str|int|float|bool|list|dict`

### Шаг 2: Валидация

Проверь:
- [ ] Pipeline `configs/pipelines/{provider}/{entity}.yaml` НЕ существует
- [ ] Naming conventions: snake_case для всех идентификаторов
- [ ] Если новый provider — предупреди что нужен `configs/sources/{provider}.yaml`

### Шаг 3: Генерация файлов

Создай 7 файлов по шаблонам ниже. Создай директории если не существуют.

### Шаг 4: Регистрация

Обнови `src/bioetl/composition/factories/transformer_factory.py`:
1. Добавь import для нового трансформера
2. Добавь вызов `register_transformer()` в функцию `register_all_transformers()`

### Шаг 5: Верификация

Выполни:
```bash
make lint && pytest tests/unit/application/pipelines/{provider}/ -v --tb=short
```

---

## Шаблоны

### 1. Pipeline Config

**Путь:** `configs/pipelines/{provider}/{entity}.yaml`

```yaml
# =============================================================================
# {PROVIDER_TITLE} {ENTITY_TITLE} Pipeline Configuration
# =============================================================================
# Minimal config using convention-based path resolution (ADR-029).
# Auto-computed paths from provider/entity_type.
#
# Convention-based defaults:
#   source_file: ../../sources/{provider}.yaml
#   dq_config_file: ../../dq/entities/{provider}/{entity}.yaml
#   filter_config_file: ../../filter/entities/{provider}/{entity}.yaml
#   sink.*.path: data/output/{layer}/{provider}/{entity}

pipeline_name: {provider}_{entity}
provider: {provider}
entity_type: {entity}
version: "1.0.0"
description: "Extract {entity} records from {PROVIDER_TITLE} API"

primary_keys: ["{primary_key}"]
silver_table: "{provider}_{entity}"
gold_table: "{provider}_{entity}"

# Batch processing
batch_size: 100
checkpoint_interval: 1000
```

### 2. DQ Config

**Путь:** `configs/dq/entities/{provider}/{entity}.yaml`

```yaml
# =============================================================================
# {PROVIDER_TITLE} {ENTITY_TITLE} DQ Rules
# =============================================================================
# Inherits from: _defaults.yaml -> providers/{provider}.yaml

version: "1.0.0"
provider: {provider}
entity: {entity}

# Entity-specific field validations
entity_field_validations:
  - field: {primary_key}
    type: required
    nullable: false
    error_message: "{primary_key} is required"
{FIELD_VALIDATIONS}

# Cross-field validations
entity_cross_field_validations: []

# Conditional validations
entity_conditional_validations: []
```

### 3. Filter Config

**Путь:** `configs/filter/entities/{provider}/{entity}.yaml`

```yaml
# =============================================================================
# {PROVIDER_TITLE} {ENTITY_TITLE} Filter Configuration
# =============================================================================

version: "1.0.0"
provider: {provider}
entity: {entity}

input_filter:
  enabled: false

gold_filters:
  required_fields:
    - {primary_key}
  columns: {}
```

### 4. Domain Entity

**Путь:** `src/bioetl/domain/entities/{provider}.py` (создать или дополнить)

```python
"""{PROVIDER_TITLE} domain entities."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.entities.base import BaseEntity


@dataclass(frozen=True, kw_only=True)
class {ProviderEntity}(BaseEntity):
    """{PROVIDER_TITLE} {ENTITY_TITLE} domain entity.

    Attributes:
        {primary_key}: Primary identifier.
{FIELD_DOCSTRINGS}
    """

    # Primary key
    {primary_key}: str
{FIELD_DEFINITIONS}

    def __post_init__(self) -> None:
        """Validate entity invariants."""
        super().__post_init__()
        if not self.{primary_key}:
            raise ValueError("{ProviderEntity} requires {primary_key}")
```

### 5. Transformer

**Путь:** `src/bioetl/application/pipelines/{provider}/{entity}_transformer.py`

```python
"""{PROVIDER_TITLE} {ENTITY_TITLE} Transformer.

Transforms raw {provider} {entity} records to Silver-layer format.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.domain.entities.{provider} import {ProviderEntity}
from bioetl.domain.services import IdentityService

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import GoldFilterConfig
    from bioetl.domain.ports import (
        DataNormalizationPort,
        MetricsPort,
        PiiHasherPort,
        TracingPort,
    )
    from bioetl.domain.types import BronzeRecord, SilverRecord


class {ProviderEntity}Transformer(BaseTransformer):
    """{PROVIDER_TITLE} {entity} transformer."""

    def __init__(
        self,
        provider: str = "{provider}",
        entity_type: str = "{entity}",
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        gold_filters: GoldFilterConfig | None = None,
        identity_service: IdentityService | None = None,
        pii_hasher: PiiHasherPort | None = None,
        data_normalizer: DataNormalizationPort | None = None,
    ) -> None:
        """Initialize transformer."""
        super().__init__(
            provider,
            entity_type=entity_type,
            tracer=tracer,
            metrics=metrics,
            gold_filters=gold_filters,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
            data_normalizer=data_normalizer,
        )

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Transform Bronze record to Silver format.

        Args:
            context: Pipeline context with run_id, logger.
            record: Raw Bronze record.
            index: Record index in batch.

        Returns:
            SilverRecord dict or None if skipped.
        """
        # Extract primary key
        {primary_key} = self._get_required_field(record, "{primary_key}")

        # Build business data
        business_data: dict[str, Any] = {
            "{primary_key}": str({primary_key}),
{FIELD_EXTRACTIONS}
        }

        # Compute identity
        entity_id = self.compute_entity_id(
            source_id=str({primary_key}),
            record={"{primary_key}": {primary_key}},
        )
        content_hash = self.compute_content_hash(business_data, exclude_none=True)

        # Create domain entity
        entity = self._create_entity(
            {ProviderEntity},
            context,
            entity_id=entity_id,
            content_hash=content_hash,
            index=index,
            **business_data,
        )

        return cast("SilverRecord", self.entity_to_silver_record(entity))
```

### 6. Gold Schema

**Путь:** `src/bioetl/domain/contracts/gold/{provider}.py` (создать или дополнить)

```python
"""{PROVIDER_TITLE} Gold layer data contracts."""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series


class {ProviderEntity}GoldSchema(pa.DataFrameModel):
    """Schema for {PROVIDER_TITLE} {ENTITY_TITLE} in Gold layer."""

    # System fields
    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)

    # Primary key
    {primary_key}: Series[str] = pa.Field(nullable=False)

{SCHEMA_FIELDS}

    # Lineage fields
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        """Pandera configuration."""

        strict = True
        coerce = True
```

### 7. Unit Tests

**Путь:** `tests/unit/application/pipelines/{provider}/test_{entity}_transformer.py`

```python
"""Unit tests for {PROVIDER_TITLE} {ENTITY_TITLE} transformer."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.application.pipelines.{provider}.{entity}_transformer import (
    {ProviderEntity}Transformer,
)
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunType


@pytest.fixture
def mock_context() -> PipelineContext:
    """Create mock pipeline context."""
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    mock_logger.warning = MagicMock()
    return PipelineContext(
        run_id=uuid4(),
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )


@pytest.fixture
def transformer() -> {ProviderEntity}Transformer:
    """Create transformer instance."""
    return {ProviderEntity}Transformer()


@pytest.mark.unit
class Test{ProviderEntity}Transformer:
    """Tests for {ProviderEntity}Transformer."""

    @pytest.mark.asyncio
    async def test_transform_valid_record(
        self,
        transformer: {ProviderEntity}Transformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test transformation of valid record."""
        record = {
            "{primary_key}": "test_123",
{TEST_RECORD_FIELDS}
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["{primary_key}"] == "test_123"
        assert "entity_id" in result
        assert "content_hash" in result
        assert "_run_id" in result

    @pytest.mark.asyncio
    async def test_transform_missing_primary_key(
        self,
        transformer: {ProviderEntity}Transformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test transformation returns None for missing primary key."""
        record: dict[str, str] = {}

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None

    @pytest.mark.asyncio
    async def test_content_hash_deterministic(
        self,
        transformer: {ProviderEntity}Transformer,
        mock_context: PipelineContext,
    ) -> None:
        """Test content_hash is deterministic."""
        record = {
            "{primary_key}": "test_123",
{TEST_RECORD_FIELDS}
        }

        result1 = await transformer.transform(mock_context, record, index=0)
        result2 = await transformer.transform(mock_context, record, index=0)

        assert result1 is not None
        assert result2 is not None
        assert result1["content_hash"] == result2["content_hash"]
```

---

## Переменные подстановки

| Переменная | Пример | Описание |
|------------|--------|----------|
| `{provider}` | `chembl` | snake_case провайдер |
| `{entity}` | `mechanism` | snake_case сущность |
| `{PROVIDER_TITLE}` | `ChEMBL` | Title case провайдер |
| `{ENTITY_TITLE}` | `Mechanism` | Title case сущность |
| `{ProviderEntity}` | `ChemblMechanism` | PascalCase класс |
| `{primary_key}` | `mechanism_id` | snake_case первичный ключ |
| `{FIELD_*}` | ... | Сгенерированные поля |

---

## Naming Conventions

| Элемент | Формат | Пример |
|---------|--------|--------|
| Pipeline name | `{provider}_{entity}` | `chembl_mechanism` |
| Table name | `{provider}_{entity}` | `chembl_mechanism` |
| Entity class | `{Provider}{Entity}` | `ChemblMechanism` |
| Transformer class | `{Provider}{Entity}Transformer` | `ChemblMechanismTransformer` |
| Schema class | `{Provider}{Entity}GoldSchema` | `ChemblMechanismGoldSchema` |
| Test class | `Test{Provider}{Entity}Transformer` | `TestChemblMechanismTransformer` |

---

## Пример полного вызова

```
User: /new-pipeline chembl mechanism

Claude: Создаю пайплайн для ChEMBL Mechanism...

Вопросы:
1. Primary key field name? → mechanism_id
2. Business fields (name:type:nullable)?
   → action_type:str:true
   → mechanism_of_action:str:true
   → target_chembl_id:str:true
   → molecule_chembl_id:str:true

Создаю файлы:
✓ configs/pipelines/chembl/mechanism.yaml
✓ configs/dq/entities/chembl/mechanism.yaml
✓ configs/filter/entities/chembl/mechanism.yaml
✓ src/bioetl/domain/entities/chembl.py (updated)
✓ src/bioetl/application/pipelines/chembl/mechanism_transformer.py
✓ src/bioetl/domain/contracts/gold/chembl.py (updated)
✓ tests/unit/application/pipelines/chembl/test_mechanism_transformer.py
✓ src/bioetl/composition/factories/transformer_factory.py (updated)

Верификация:
$ make lint && pytest tests/unit/application/pipelines/chembl/test_mechanism_transformer.py -v
...
OK
```
