"""Validated, non-secret runtime configuration for platform services."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum


class ConfigurationError(ValueError):
    """Raised when required runtime configuration is missing or invalid."""


class AppEnvironment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class ModelProvider(StrEnum):
    NONE = "none"
    OPENAI = "openai"
    GOOGLE = "google"


_REQUIRED_CONNECTION_KEYS = (
    "DATABASE_URL",
    "KAFKA_BOOTSTRAP_SERVERS",
    "REDIS_URL",
    "MILVUS_URI",
    "OBJECT_STORAGE_ENDPOINT",
)


@dataclass(frozen=True, slots=True)
class AppSettings:
    """Configuration safe to pass through service initialization and telemetry."""

    environment: AppEnvironment
    service_name: str
    database_url: str
    kafka_bootstrap_servers: str
    redis_url: str
    milvus_uri: str
    object_storage_endpoint: str
    object_storage_bucket: str | None
    model_provider: ModelProvider

    @classmethod
    def from_mapping(cls, values: Mapping[str, str]) -> AppSettings:
        """Create settings from environment-like values without reading global state."""

        environment = _parse_enum(AppEnvironment, values.get("APP_ENV", "development"), "APP_ENV")
        provider = _parse_enum(
            ModelProvider, values.get("MODEL_PROVIDER", "none"), "MODEL_PROVIDER"
        )

        missing = [key for key in _REQUIRED_CONNECTION_KEYS if not values.get(key)]
        if environment is AppEnvironment.PRODUCTION and not values.get("OBJECT_STORAGE_BUCKET"):
            missing.append("OBJECT_STORAGE_BUCKET")
        if missing:
            joined = ", ".join(sorted(missing))
            raise ConfigurationError(f"Missing required environment variable(s): {joined}")

        return cls(
            environment=environment,
            service_name=values.get("SERVICE_NAME", "vision-safety-platform"),
            database_url=values["DATABASE_URL"],
            kafka_bootstrap_servers=values["KAFKA_BOOTSTRAP_SERVERS"],
            redis_url=values["REDIS_URL"],
            milvus_uri=values["MILVUS_URI"],
            object_storage_endpoint=values["OBJECT_STORAGE_ENDPOINT"],
            object_storage_bucket=values.get("OBJECT_STORAGE_BUCKET"),
            model_provider=provider,
        )

    def required_secret_names(self) -> tuple[str, ...]:
        """Return provider secrets that must be resolved outside application config."""

        if self.model_provider is ModelProvider.OPENAI:
            return ("OPENAI_API_KEY",)
        if self.model_provider is ModelProvider.GOOGLE:
            return ("GOOGLE_API_KEY",)
        return ()


def _parse_enum[T: StrEnum](enum_type: type[T], raw_value: str, variable_name: str) -> T:
    try:
        return enum_type(raw_value.lower())
    except ValueError as error:
        allowed = ", ".join(member.value for member in enum_type)
        raise ConfigurationError(f"{variable_name} must be one of: {allowed}") from error
