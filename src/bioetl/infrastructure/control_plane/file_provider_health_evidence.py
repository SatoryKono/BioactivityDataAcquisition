"""File adapter for compact provider-health CURRENT evidence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from bioetl.infrastructure.control_plane._file_lineage_index import stable_key_filename
from bioetl.infrastructure.storage.atomic import atomic_write_text

PROVIDER_HEALTH_EVIDENCE_SCHEMA = "provider_health_evidence_v1"
PROVIDER_HEALTH_FRESHNESS_SECONDS = 15 * 60

__all__ = [
    "PROVIDER_HEALTH_EVIDENCE_SCHEMA",
    "PROVIDER_HEALTH_FRESHNESS_SECONDS",
    "FileProviderHealthEvidenceStore",
    "ProviderHealthEvidenceRecord",
]


@dataclass(frozen=True, slots=True)
class ProviderHealthEvidenceRecord:
    """One persisted provider-health observation."""

    provider: str
    status: int
    observed_at: str
    endpoint: str
    reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": PROVIDER_HEALTH_EVIDENCE_SCHEMA,
            "provider": self.provider,
            "status": self.status,
            "observed_at": self.observed_at,
            "endpoint": self.endpoint,
            "reason": self.reason,
        }

    def observed_unix(self) -> float | None:
        try:
            return datetime.fromisoformat(self.observed_at).timestamp()
        except ValueError:
            return None

    def is_fresh(self, *, now: datetime | None = None) -> bool:
        observed = self.observed_unix()
        if observed is None:
            return False
        current = (now or datetime.now(UTC)).timestamp()
        return 0.0 <= current - observed <= PROVIDER_HEALTH_FRESHNESS_SECONDS


@dataclass(slots=True)
class FileProviderHealthEvidenceStore:
    """Persist one JSON record per provider next to control-plane stores."""

    base_path: Path

    def path_for(self, provider: str) -> Path:
        return self.base_path / f"{stable_key_filename(provider)}.json"

    def persist(self, record: ProviderHealthEvidenceRecord) -> None:
        path = self.path_for(record.provider)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            record.to_dict(), ensure_ascii=False, indent=2, sort_keys=True
        ) + chr(10)
        atomic_write_text(path, payload)

    def load(self, provider: str) -> ProviderHealthEvidenceRecord | None:
        return _record_from_path(self.path_for(provider))

    def list_all(self) -> tuple[ProviderHealthEvidenceRecord, ...]:
        if not self.base_path.is_dir():
            return ()
        records: list[ProviderHealthEvidenceRecord] = []
        for path in sorted(self.base_path.iterdir()):
            if path.is_file() and path.suffix == ".json":
                record = _record_from_path(path)
                if record is not None:
                    records.append(record)
        return tuple(records)


def _record_from_path(path: Path) -> ProviderHealthEvidenceRecord | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    provider = payload.get("provider")
    status = payload.get("status")
    observed_at = payload.get("observed_at")
    endpoint = payload.get("endpoint")
    if not isinstance(provider, str) or not provider.strip():
        return None
    if not isinstance(status, int) or status not in {0, 1, 2}:
        return None
    if not isinstance(observed_at, str) or not observed_at.strip():
        return None
    if not isinstance(endpoint, str):
        endpoint = ""
    reason = payload.get("reason")
    if reason is not None and not isinstance(reason, str):
        reason = None
    return ProviderHealthEvidenceRecord(
        provider=provider.strip(),
        status=status,
        observed_at=observed_at.strip(),
        endpoint=endpoint.strip(),
        reason=reason.strip() if isinstance(reason, str) and reason.strip() else None,
    )
