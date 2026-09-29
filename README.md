# Production Agentic Vision System for Construction Safety

This repository is a clean foundation for an enterprise, evidence-first construction-safety platform. The prior MVP is preserved on the `old-dev` branch.

## Target workflow

`Login → safety dashboard → media upload → API Gateway → Kafka inspection pipeline → scene / ROI / specialist agents → Milvus OSHA retrieval → LLM-as-a-Judge → decision gate → safety event or HITL review`

## Project structure

| Directory | Owns |
| --- | --- |
| `apps/web` | React dashboard, upload, inspection status, and HITL review. |
| `services` | API Gateway, ingestion, event-driven AI workers, decision gate, and HITL service. |
| `packages/contracts` | Versioned API and Kafka event schemas. |
| `packages/shared` | Shared libraries that have a true cross-service owner. |
| `infra` | Local development, Kubernetes, secrets, networking, and deployment definitions. |
| `docs/adr` | Architecture decision records. |
| `docs/runbooks` | Operational, incident, and recovery procedures. |
| `evals` | Golden datasets, regression scenarios, and evaluation reports. |
| `tests` | Contract and end-to-end integration tests. |

## Non-negotiable product principles

- AI output is a candidate observation, not a confirmed safety or legal finding.
- Every accepted event needs visual evidence, an OSHA citation, confidence policy evaluation, and an audit trail.
- High-severity, uncertain, unsupported, or conflicting findings route to HITL.
- Kafka consumers are idempotent; retries are bounded; poison messages go to DLQs.
- Every inspection propagates `tenant_id`, `inspection_id`, `trace_id`, schema version, model/prompt version, token usage, cost, and latency.

## Begin here

Read [CODEX.md](CODEX.md) before implementing any service. It defines build order, contracts, testing, security, and agent coordination rules.
