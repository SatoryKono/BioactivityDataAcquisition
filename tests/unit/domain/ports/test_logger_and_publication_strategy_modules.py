"""Direct unit coverage for retained domain port protocol modules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from bioetl.domain.ports.logger_port import LoggerPort
from bioetl.domain.ports.publication_strategy import (
    DataExtractorStrategy,
    IdentifierResolverStrategy,
    PublicationMetadataStrategy,
)


pytestmark = pytest.mark.unit


@dataclass
class _Logger:
    events: list[tuple[str, str, dict[str, Any]]]

    def error(self, message: str, **kwargs: Any) -> None:
        self.events.append(("error", message, dict(kwargs)))

    def warning(self, message: str, **kwargs: Any) -> None:
        self.events.append(("warning", message, dict(kwargs)))

    def info(self, message: str, **kwargs: Any) -> None:
        self.events.append(("info", message, dict(kwargs)))

    def debug(self, message: str, **kwargs: Any) -> None:
        self.events.append(("debug", message, dict(kwargs)))


class _PublicationStrategy:
    def pre_extract_validation(
        self,
        context: object,
        record: dict[str, Any],
        index: int,
    ) -> None:
        self.last_validation = (context, record, index)

    def extract_business_data(self, record: dict[str, Any]) -> dict[str, Any]:
        return {"source": record["source"]}

    def get_primary_id_field(self) -> str:
        return "publication_id"

    def validate_primary_id(
        self,
        context: object,
        business_data: dict[str, Any],
        index: int,
    ) -> tuple[str, Any] | None:
        del context, index
        value = business_data.get("publication_id")
        return ("publication_id", value) if value else None

    def get_entity_class(self) -> type[object]:
        return object

    def should_log_fallback_lookup(self) -> bool:
        return True

    def post_process_silver_record(self, silver_record: dict[str, Any]) -> dict[str, Any]:
        return {**silver_record, "post_processed": True}


def test_logger_port_runtime_check_and_methods() -> None:
    logger = _Logger(events=[])

    assert isinstance(logger, LoggerPort)

    logger.error("failed", code="E")
    logger.warning("warning", retry=True)
    logger.info("started", run_id="run-1")
    logger.debug("debug", payload={"x": 1})

    assert logger.events == [
        ("error", "failed", {"code": "E"}),
        ("warning", "warning", {"retry": True}),
        ("info", "started", {"run_id": "run-1"}),
        ("debug", "debug", {"payload": {"x": 1}}),
    ]


def test_publication_strategy_protocols_are_runtime_checkable() -> None:
    strategy = _PublicationStrategy()

    assert isinstance(strategy, DataExtractorStrategy)
    assert isinstance(strategy, IdentifierResolverStrategy)
    assert isinstance(strategy, PublicationMetadataStrategy)

    strategy.pre_extract_validation(object(), {"source": "crossref"}, 3)
    assert strategy.extract_business_data({"source": "crossref"}) == {
        "source": "crossref"
    }
    assert strategy.get_primary_id_field() == "publication_id"
    assert strategy.validate_primary_id(
        object(),
        {"publication_id": "10.123/example"},
        0,
    ) == ("publication_id", "10.123/example")
    assert strategy.validate_primary_id(object(), {}, 0) is None
    assert strategy.get_entity_class() is object
    assert strategy.should_log_fallback_lookup() is True
    assert strategy.post_process_silver_record({"id": "P1"}) == {
        "id": "P1",
        "post_processed": True,
    }
