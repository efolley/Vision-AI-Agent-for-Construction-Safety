"""Secret-provider interfaces that keep secret retrieval outside configuration."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from typing import Protocol


class SecretProvider(Protocol):
    """Resolves a named secret without exposing provider-specific implementation."""

    def get(self, name: str) -> str | None: ...


class EnvironmentSecretProvider:
    """Development-only provider reading an injected mapping or process environment."""

    def __init__(self, values: Mapping[str, str] | None = None) -> None:
        self._values = values if values is not None else os.environ

    def get(self, name: str) -> str | None:
        value = self._values.get(name)
        return value if value else None


class MappingSecretProvider:
    """In-memory provider for tests and adapter development."""

    def __init__(self, values: Mapping[str, str]) -> None:
        self._values = values

    def get(self, name: str) -> str | None:
        value = self._values.get(name)
        return value if value else None


class ChainedSecretProvider:
    """Queries providers in priority order; production adapters should come first."""

    def __init__(self, providers: Sequence[SecretProvider]) -> None:
        self._providers = providers

    def get(self, name: str) -> str | None:
        for provider in self._providers:
            if value := provider.get(name):
                return value
        return None


def require_secrets(settings_secret_names: Sequence[str], provider: SecretProvider) -> None:
    """Fail closed when a configured model provider has unresolved required secrets."""

    missing = [name for name in settings_secret_names if provider.get(name) is None]
    if missing:
        raise RuntimeError(f"Required secret(s) unavailable: {', '.join(sorted(missing))}")
