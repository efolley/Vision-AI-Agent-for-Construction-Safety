# Local development workflow

## Prerequisites

- Python 3.12 or newer and [uv](https://docs.astral.sh/uv/)
- Docker and Docker Compose (required once infrastructure services are added)

## First run

```bash
cp .env.example .env
uv sync --all-extras
make check
```

`uv` owns the project environment, dependency resolution, and `uv.lock`. Do not install project dependencies directly with `pip`. `make check` runs formatting verification, linting, strict type checking, and all tests. Use `make format` to apply formatting.

## Configuration and secrets

- Keep non-secret settings in `.env`; it is ignored by Git.
- `.env.example` documents required keys and safe local defaults.
- Services receive an `AppSettings` instance created from environment values. It contains connection configuration only, never provider credentials.
- Services resolve `OPENAI_API_KEY` or `GOOGLE_API_KEY` through the `SecretProvider` interface. Environment variables are permitted for local development only.
- Production deployments must provide an adapter for the organization-approved secret manager and must not place plaintext secrets in Kubernetes manifests, Docker Compose files, logs, or traces.

## Commands

| Command | Purpose |
| --- | --- |
| `make bootstrap` | Resolve and install the development toolchain through uv. |
| `make format` | Apply Ruff formatting. |
| `make format-check` | Verify formatting without modifying files. |
| `make lint` | Run Ruff lint rules. |
| `make typecheck` | Run strict mypy checks. |
| `make test` | Run all Python tests through uv. |
| `make check` | Run all verification commands. |
