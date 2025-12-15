"""Configuration management for BioETL.

Implements strict configuration validation using Pydantic Settings.
Centralizes all environment variable reading and typing.
"""

from typing import Literal

from pydantic import Field, RedisDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application settings."""

    # AWS / S3 Configuration
    AWS_ENDPOINT_URL: str | None = Field(default=None, description="S3 Endpoint URL (for MinIO)")
    AWS_ACCESS_KEY_ID: str | None = Field(default=None, description="AWS Access Key")
    AWS_SECRET_ACCESS_KEY: SecretStr | None = Field(default=None, description="AWS Secret Key")

    # Bucket Names
    BIOETL_S3_BUCKET_BRONZE: str = Field(default="bioetl-bronze", description="Bronze layer bucket")
    BIOETL_S3_BUCKET_SILVER: str = Field(default="bioetl-silver", description="Silver layer bucket")
    BIOETL_S3_BUCKET_CHECKPOINTS: str = Field(default="bioetl-checkpoints", description="Checkpoint bucket")

    # Redis Configuration
    BIOETL_REDIS_HOST: str = Field(default="localhost", description="Redis host")
    BIOETL_REDIS_PORT: int = Field(default=6379, description="Redis port")

    # ChEMBL Configuration
    BIOETL_CHEMBL_API_URL: str = Field(
        default="https://www.ebi.ac.uk/chembl/api/data",
        description="ChEMBL API Base URL"
    )

    # Logging
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FORMAT_JSON: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def redis_url(self) -> str:
        """Construct Redis URL from host and port."""
        return f"redis://{self.BIOETL_REDIS_HOST}:{self.BIOETL_REDIS_PORT}"


# Global settings instance
settings = Settings()
