from typing import Protocol, Iterator, Any
from datetime import datetime

class Query(Protocol):
    """Marker protocol for query objects."""
    pass

class RawRecord(Protocol):
    """Raw data record protocol."""
    data: dict[str, Any]
    ingestion_ts: datetime

# Rule 1.1.1: Design-time enforcement via Protocol
class DataSourcePort(Protocol):
    async def fetch(self, query: Query) -> Iterator[RawRecord]:
        """Fetch data from upstream source."""
        ...

    async def health_check(self) -> bool:
        """Rule 3.5: Provider Health Monitoring hook."""
        ...

class StateManagerPort(Protocol):
    def save_checkpoint(self, pipeline: str, state: dict[str, Any]) -> None: ...
    def load_checkpoint(self, pipeline: str) -> dict[str, Any]: ...
