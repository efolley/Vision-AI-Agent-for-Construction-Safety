# Local development workflow

## Prerequisites

- Python 3.12 or newer
- Docker and Docker Compose (required once infrastructure services are added)

## First run

```bash
cp .env.example .env
python3 -m venv .venv
. .venv/bin/activate
make bootstrap
make check
```

`make check` runs formatting verification, linting, strict type checking, and the Phase 0 test suite. Use `make format` to apply formatting.

## Configuration and secrets

- Keep non-secret settings in `.env`; it is ignored by Git.
- `.env.example` documents required keys and safe local defaults.
- Services receive an `AppSettings` instance created from environment values. It contains connection configuration only, never provider credentials.
- Services resolve `OPENAI_API_KEY` or `GOOGLE_API_KEY` through the `SecretProvider` interface. Environment variables are permitted for local development only.
- Production deployments must provide an adapter for the organization-approved secret manager and must not place plaintext secrets in Kubernetes manifests, Docker Compose files, logs, or traces.

## Commands

| Command | Purpose |
| --- | --- |
| `make bootstrap` | Install the development toolchain. |
| `make format` | Apply Ruff formatting. |
| `make format-check` | Verify formatting without modifying files. |
| `make lint` | Run Ruff lint rules. |
| `make typecheck` | Run strict mypy checks. |
| `make test` | Run the standard-library Phase 0 tests. |
| `make check` | Run all verification commands. |
