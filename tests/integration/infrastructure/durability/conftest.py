import pytest
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.time.system_clock import SystemClock
from bioetl.infrastructure.validation import ContractAwareSilverValidator

@pytest.fixture
def test_logger():
    return NoOpLogger()

@pytest.fixture
def system_clock():
    return SystemClock()

@pytest.fixture
def silver_validator():
    import pandera.polars as pa
    class DummySchema(pa.DataFrameModel):
        id: str
    return ContractAwareSilverValidator(schema_def=DummySchema)
