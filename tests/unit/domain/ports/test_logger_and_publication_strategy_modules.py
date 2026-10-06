# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Direct unit coverage for retained domain port protocol modules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Self

import pytest

from bioetl.domain.ports.logger_port import LoggerPort
from bioetl.domain.ports.observability.logging import (
    LoggerPort as CanonicalLoggerPort,
)
from bioetl.domain.ports.publication_strategy import (
    DataExtractorStrategy,
    IdentifierResolverStrategy,
    PublicationMetadataStrategy,
)


pytestmark = pytest.mark.unit


@dataclass
class _Logger:
    events: list[tuple[str, str, dict[str, Any]]]

    def bind(self, **kwargs: Any) -> Self:
        self.events.append(("bind", "", dict(kwargs)))
        return self

    def error(self, _event: str, **kwargs: Any) -> Any:
        self.events.append(("error", _event, dict(kwargs)))

    def warning(self, _event: str, **kwargs: Any) -> Any:
        self.events.append(("warning", _event, dict(kwargs)))

    def info(self, _event: str, **kwargs: Any) -> Any:
        self.events.append(("info", _event, dict(kwargs)))

    def debug(self, _event: str, **kwargs: Any) -> Any:
        self.events.append(("debug", _event, dict(kwargs)))

    def exception(self, _event: str, **kwargs: Any) -> Any:
        self.events.append(("exception", _event, dict(kwargs)))


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

    def post_process_silver_record(
        self, silver_record: dict[str, Any]
    ) -> dict[str, Any]:
        return {**silver_record, "post_processed": True}


def test_logger_port_runtime_check_and_methods() -> None:
    logger = _Logger(events=[])

    assert LoggerPort is CanonicalLoggerPort
    assert isinstance(logger, LoggerPort)

    assert logger.bind(run_id="run-1") is logger
    logger.error("failed", code="E")
    logger.warning("warning", retry=True)
    logger.info("started", run_id="run-1")
    logger.debug("debug", payload={"x": 1})
    logger.exception("exception", exc_info=True)

    assert logger.events == [
        ("bind", "", {"run_id": "run-1"}),
        ("error", "failed", {"code": "E"}),
        ("warning", "warning", {"retry": True}),
        ("info", "started", {"run_id": "run-1"}),
        ("debug", "debug", {"payload": {"x": 1}}),
        ("exception", "exception", {"exc_info": True}),
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
