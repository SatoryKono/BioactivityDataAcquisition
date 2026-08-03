# mypy: disable-error-code="misc"
"""Bronze layer metadata models.

Contains API request tracking, source metadata, file output info,
and the complete BronzeMetadata aggregate for sidecar files.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from bioetl.domain.medallion import Layer
from bioetl.domain.models._metadata_common import (
    BaseOutputMetadata,
    EnvironmentMetadata,
    GovernanceMetadata,
    PipelineMetadata,
    RuntimeMetadata,
    validate_utc_datetime,
)

__all__ = [
    "APIRequestDetails",
    "BronzeMetadata",
    "BronzeOutputExt",
    "FileOutputMetadata",
    "InputSnapshotRef",
    "RateLimitInfo",
    "SourceMetadata",
]


class RateLimitInfo(BaseModel):
    """Rate limit information from API response headers.

    Attributes:
        remaining: Remaining requests in current window (X-RateLimit-Remaining).
        limit: Maximum requests allowed in window (X-RateLimit-Limit).
        reset_at: Timestamp when rate limit resets (X-RateLimit-Reset).
        retry_after_seconds: Seconds to wait before retry (Retry-After header).
    """

    remaining: int | None = Field(
        default=None, description="Remaining requests in current window"
    )
    limit: int | None = Field(
        default=None, description="Maximum requests allowed in window"
    )
    reset_at: datetime | None = Field(
        default=None, description="Timestamp when rate limit resets"
    )
    retry_after_seconds: float | None = Field(
        default=None, description="Seconds to wait before retry"
    )

    @field_validator("reset_at")
    @classmethod
    def _require_utc(cls, value: datetime | None) -> datetime | None:
        return validate_utc_datetime(value)


class APIRequestDetails(BaseModel):
    """Detailed API request information for audit and debugging.

    Captures per-request metadata including endpoint, parameters,
    response size, timing, and rate limit status.

    Attributes:
        endpoint: API endpoint path (e.g., "/chembl/api/data/activity").
        base_url: Base URL of the API (e.g., "https://www.ebi.ac.uk").
        query_params: Query parameters used in request.
        http_method: HTTP method (GET, POST).
        response_size_bytes: Size of response body in bytes.
        request_duration_ms: Request duration in milliseconds.
        status_code: HTTP response status code.
        rate_limit: Rate limit information from response headers.
        timestamp: UTC timestamp when request was made.
    """

    endpoint: str = Field(description="API endpoint path")
    base_url: str = Field(description="Base URL of the API")
    query_params: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict, description="Query parameters"
    )
    http_method: Literal["GET", "POST", "HEAD"] = Field(
        default="GET", description="HTTP method"
    )
    response_size_bytes: int = Field(
        default=0, description="Size of response body in bytes"
    )
    request_duration_ms: float = Field(
        default=0.0, description="Request duration in milliseconds"
    )
    status_code: int = Field(default=200, description="HTTP response status code")
    rate_limit: RateLimitInfo | None = Field(
        default=None, description="Rate limit information"
    )
    timestamp: datetime | None = Field(
        default=None, description="UTC timestamp when request was made"
    )

    @field_validator("timestamp")
    @classmethod
    def _require_utc(cls, value: datetime | None) -> datetime | None:
        return validate_utc_datetime(value)


class InputSnapshotRef(BaseModel):
    """Immutable snapshot reference for one external-input batch.

    Attributes:
        snapshot_id: Stable identifier for the captured input snapshot.
        content_hash: SHA256 hash of the captured payload bytes/content.
        immutable_uri: Immutable local/object-store URI for exact replay.
        query_fingerprint: Optional normalized query fingerprint for lookup.
        storage_provider: Optional object-storage backend/provider name.
        object_bucket: Optional object-storage bucket/container name.
        object_key: Optional object-storage object key/path.
        object_version_id: Optional object-storage object version anchor.
        etag: Optional upstream entity tag captured at fetch time.
        last_modified: Optional upstream last-modified marker.
        captured_at: UTC timestamp when the snapshot was captured.
    """

    snapshot_id: str = Field(description="Stable identifier for the input snapshot")
    content_hash: str = Field(description="SHA256 hash of the captured input content")
    immutable_uri: str | None = Field(
        default=None,
        description="Immutable URI or file path for replaying the captured payload",
    )
    query_fingerprint: str | None = Field(
        default=None,
        description="Optional normalized query fingerprint for snapshot lookup",
    )
    storage_provider: str | None = Field(
        default=None,
        description="Optional object-storage backend/provider name",
    )
    object_bucket: str | None = Field(
        default=None,
        description="Optional object-storage bucket/container name",
    )
    object_key: str | None = Field(
        default=None,
        description="Optional object-storage object key/path",
    )
    object_version_id: str | None = Field(
        default=None,
        description="Optional object-storage object version anchor",
    )
    etag: str | None = Field(
        default=None,
        description="Optional upstream entity tag captured at fetch time",
    )
    last_modified: str | None = Field(
        default=None,
        description="Optional upstream last-modified marker",
    )
    captured_at: datetime | None = Field(
        default=None,
        description="UTC timestamp when the snapshot was captured",
    )

    @field_validator("captured_at")
    @classmethod
    def _require_utc(cls, value: datetime | None) -> datetime | None:
        return validate_utc_datetime(value)


class SourceMetadata(BaseModel):
    """Data source information for Bronze layer.

    Extended to include detailed API request tracking for audit,
    debugging, and monitoring purposes.

    Attributes:
        type: Source type (api, csv, parquet).
        url: API URL for API sources.
        file_path: File path for file sources.
        query_string: Query string used for data source filtering
            (e.g., 'assay_type=B&standard_type=IC50').
        api_version: Provider API version.
        api_requests: List of detailed API request information.
        total_requests: Total number of API requests made.
        total_response_bytes: Total bytes received from all requests.
        avg_request_duration_ms: Average request duration in milliseconds.
        input_snapshots: Immutable snapshot references for replayable input batches.
    """

    type: Literal["api", "csv", "parquet"] = Field(
        default="api", description="Source type"
    )
    url: str | None = Field(default=None, description="API URL")
    file_path: str | None = Field(default=None, description="Source file path")
    query_string: str | None = Field(
        default=None,
        description="Query string used for data source filtering (e.g., 'assay_type=B')",
    )
    api_version: str | None = Field(default=None, description="Provider API version")
    api_requests: list[APIRequestDetails] = Field(
        default_factory=list, description="Detailed API request information"
    )
    total_requests: int = Field(default=0, description="Total number of API requests")
    total_response_bytes: int = Field(
        default=0, description="Total bytes received from all requests"
    )
    avg_request_duration_ms: float = Field(
        default=0.0, description="Average request duration in milliseconds"
    )
    input_snapshots: list[InputSnapshotRef] = Field(
        default_factory=list,
        description="Immutable snapshot references for replayable input batches",
    )


class FileOutputMetadata(BaseModel):
    """Individual file output information.

    Attributes:
        path: Relative file path.
        size_bytes: File size in bytes.
        record_count: Number of records in file.
        checksum_blake2: BLAKE2 checksum for integrity.
    """

    path: str = Field(description="Relative file path")
    size_bytes: int = Field(description="File size in bytes")
    record_count: int = Field(description="Number of records")
    checksum_blake2: str | None = Field(default=None, description="BLAKE2 checksum")


class BronzeOutputExt(BaseModel):
    """Bronze-specific output metadata extension.

    Tracks individual files for append-only Bronze layer.

    Attributes:
        files: List of output files with per-file metrics.
        format: Output format (jsonl+zstd, jsonl, etc.).
        compression: Compression algorithm.
    """

    files: list[FileOutputMetadata] = Field(
        default_factory=list,
        description="List of output files with per-file metrics",
    )
    format: str = Field(
        default="jsonl+zstd",
        description="Output format (jsonl+zstd, jsonl, etc.)",
    )
    compression: str = Field(
        default="zstd",
        description="Compression algorithm",
    )


class BronzeMetadata(BaseModel):
    """Complete metadata for Bronze layer sidecar file.

    Structure follows RULES.md 2.4 lineage requirements.
    Includes governance metadata block for data stewardship.

    ADR-029: Uses unified BaseOutputMetadata + BronzeOutputExt composition.
    """

    version: str = Field(default="1.1", description="Metadata schema version")
    layer: Layer = Field(default=Layer.BRONZE, description="Medallion layer")
    runtime: RuntimeMetadata = Field(description="Runtime context")
    pipeline: PipelineMetadata = Field(description="Pipeline identification")
    source: SourceMetadata = Field(
        default_factory=SourceMetadata, description="Source information"
    )
    output: BaseOutputMetadata = Field(
        default_factory=BaseOutputMetadata, description="Base output metrics"
    )
    output_ext: BronzeOutputExt = Field(
        default_factory=BronzeOutputExt, description="Bronze-specific output metrics"
    )
    environment: EnvironmentMetadata = Field(description="Environment information")
    governance: GovernanceMetadata | None = Field(
        default=None, description="Governance metadata for data stewardship"
    )
