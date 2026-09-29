from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "packages" / "shared" / "python"))

from vision_safety_core.config import (  # noqa: E402
    AppEnvironment,
    AppSettings,
    ConfigurationError,
    ModelProvider,
)
from vision_safety_core.secrets import (  # noqa: E402
    ChainedSecretProvider,
    EnvironmentSecretProvider,
    MappingSecretProvider,
    require_secrets,
)


def valid_values(**overrides: str) -> dict[str, str]:
    values = {
        "APP_ENV": "development",
        "SERVICE_NAME": "test-service",
        "DATABASE_URL": "postgresql://localhost/safety",
        "KAFKA_BOOTSTRAP_SERVERS": "localhost:9092",
        "REDIS_URL": "redis://localhost:6379/0",
        "MILVUS_URI": "http://localhost:19530",
        "OBJECT_STORAGE_ENDPOINT": "http://localhost:9000",
        "MODEL_PROVIDER": "none",
    }
    values.update(overrides)
    return values


class AppSettingsTests(unittest.TestCase):
    def test_valid_development_settings(self) -> None:
        settings = AppSettings.from_mapping(valid_values())

        self.assertEqual(settings.environment, AppEnvironment.DEVELOPMENT)
        self.assertEqual(settings.service_name, "test-service")

    def test_missing_connection_values_are_reported(self) -> None:
        values = valid_values()
        del values["DATABASE_URL"]
        del values["MILVUS_URI"]

        with self.assertRaisesRegex(ConfigurationError, "DATABASE_URL, MILVUS_URI"):
            AppSettings.from_mapping(values)

    def test_invalid_environment_is_rejected(self) -> None:
        with self.assertRaisesRegex(ConfigurationError, "APP_ENV must be one of"):
            AppSettings.from_mapping(valid_values(APP_ENV="local"))

    def test_invalid_model_provider_is_rejected(self) -> None:
        with self.assertRaisesRegex(ConfigurationError, "MODEL_PROVIDER must be one of"):
            AppSettings.from_mapping(valid_values(MODEL_PROVIDER="anthropic"))

    def test_environment_and_provider_are_case_insensitive(self) -> None:
        settings = AppSettings.from_mapping(valid_values(APP_ENV="TEST", MODEL_PROVIDER="OPENAI"))

        self.assertEqual(settings.environment, AppEnvironment.TEST)
        self.assertEqual(settings.model_provider, ModelProvider.OPENAI)

    def test_production_requires_object_storage_bucket(self) -> None:
        with self.assertRaisesRegex(ConfigurationError, "OBJECT_STORAGE_BUCKET"):
            AppSettings.from_mapping(valid_values(APP_ENV="production"))

    def test_openai_provider_requires_openai_secret_name(self) -> None:
        settings = AppSettings.from_mapping(valid_values(MODEL_PROVIDER="openai"))

        self.assertEqual(settings.required_secret_names(), ("OPENAI_API_KEY",))

    def test_no_provider_requires_no_secrets(self) -> None:
        settings = AppSettings.from_mapping(valid_values())

        self.assertEqual(settings.required_secret_names(), ())


class SecretProviderTests(unittest.TestCase):
    def test_mapping_provider_returns_present_secret(self) -> None:
        provider = MappingSecretProvider({"OPENAI_API_KEY": "secret-value"})

        self.assertEqual(provider.get("OPENAI_API_KEY"), "secret-value")

    def test_mapping_provider_hides_blank_secret(self) -> None:
        provider = MappingSecretProvider({"OPENAI_API_KEY": ""})

        self.assertIsNone(provider.get("OPENAI_API_KEY"))

    def test_environment_provider_uses_injected_values(self) -> None:
        provider = EnvironmentSecretProvider({"GOOGLE_API_KEY": "google-secret"})

        self.assertEqual(provider.get("GOOGLE_API_KEY"), "google-secret")

    def test_chain_uses_first_available_provider(self) -> None:
        provider = ChainedSecretProvider(
            [
                MappingSecretProvider({"TOKEN": "primary"}),
                MappingSecretProvider({"TOKEN": "fallback"}),
            ]
        )

        self.assertEqual(provider.get("TOKEN"), "primary")

    def test_required_secrets_fails_closed(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "OPENAI_API_KEY"):
            require_secrets(("OPENAI_API_KEY",), MappingSecretProvider({}))

    def test_required_secrets_accepts_available_secret(self) -> None:
        require_secrets(("OPENAI_API_KEY",), MappingSecretProvider({"OPENAI_API_KEY": "present"}))
