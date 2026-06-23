"""Response mapping helpers for CrossRef adapter flows."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.types import BronzeRecord, HealthStatus
from bioetl.infrastructure.adapters.health_probe_policy import (
    DEFAULT_SLOW_HEALTH_PROBE_THRESHOLD_SECONDS,
    is_slow_health_probe,
)
from bioetl.infrastructure.adapters.health_status_policy import (
    classify_health_probe_status,
)

__all__ = [
    "CrossRefHealthProbeMapping",
    "CrossRefResponseMapper",
]


@dataclass(frozen=True, slots=True)
class CrossRefHealthProbeMapping:
    """Mapped health probe outcome with optional log event."""

    status: HealthStatus
    event_name: str | None


class CrossRefResponseMapper:
    """Map raw CrossRef payloads to adapter-level semantics."""

    @staticmethod
    def with_lookup_method(
        publication: BronzeRecord,
        lookup_method: str,
    ) -> BronzeRecord:
        """Annotate publication payload with lookup metadata.

        Args:
            publication: Bronze record to annotate in-place.
            lookup_method: Lookup method label to set in the _lookup_method field.

        Returns:
            Publication record with the _lookup_method field set to the given value.
        """
        publication["_lookup_method"] = lookup_method
        return publication

    @staticmethod
    def map_health_probe(
        *,
        status_code: int,
        elapsed_seconds: float,
        slow_threshold_seconds: float = DEFAULT_SLOW_HEALTH_PROBE_THRESHOLD_SECONDS,
    ) -> CrossRefHealthProbeMapping:
        """Map raw probe response to adapter health status and event metadata.

        Args:
            status_code: HTTP response status code from the health probe request.
            elapsed_seconds: Request duration in seconds for latency classification.
            slow_threshold_seconds: Duration threshold above which DEGRADED is returned.

        Returns:
            CrossRefHealthProbeMapping with the classified HealthStatus and optional log event name.
        """
        if status_code != 200:
            status = classify_health_probe_status(status_code)
            event_name = (
                "crossref_health_check_degraded"
                if status == HealthStatus.DEGRADED
                else "crossref_health_check_failed"
            )
            return CrossRefHealthProbeMapping(status=status, event_name=event_name)

        if is_slow_health_probe(
            elapsed_seconds=elapsed_seconds,
            slow_threshold_seconds=slow_threshold_seconds,
        ):
            return CrossRefHealthProbeMapping(
                status=HealthStatus.DEGRADED,
                event_name="crossref_health_check_slow",
            )

        return CrossRefHealthProbeMapping(status=HealthStatus.HEALTHY, event_name=None)
