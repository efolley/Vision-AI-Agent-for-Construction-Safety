# Build Guide for Codex Agents

## Mission

Build an enterprise, multi-tenant construction-safety inspection platform. It processes jobsite images and video frames asynchronously, produces evidence-backed candidate safety events, and routes uncertain or high-severity cases to human-in-the-loop (HITL) review.

The system must optimize for **safety, auditability, reliability, and cost control** over demo speed. Never represent an AI observation as a confirmed OSHA violation without visual evidence, retrieved criteria, and policy evaluation.

## Required architecture

Build these components in this order:

1. `src/api-gateway`: OIDC/JWT authentication, tenant authorization, rate limits, Redis-backed idempotency, request IDs, and upload policy.
2. `src/ingestion`: validate media, store originals, create inspection records, and publish `inspection.requested.v1` only after durable persistence.
3. `packages/contracts`: versioned schemas for API payloads and Kafka events. Contract changes are backward compatible or released under a new version.
4. Event workers: scene analyzer → ROI router → PPE/scaffold/proximity inspectors → evidence synthesizer.
5. `src/osha-retrieval`: hybrid lexical and Milvus vector retrieval over a versioned OSHA corpus; return exact excerpts, source versions, and scores.
6. `src/llm-judge`: evaluate whether evidence supports the candidate claim and whether the cited OSHA criterion is relevant.
7. `src/decision-gate`: validate all input, apply calibrated thresholds and severity policy, then persist either a safety event or HITL task.
8. `src/evidence-renderer`: deterministically render validated ROI boxes/polygons, severity, confidence, and OSHA citations; preserve the original media separately.
9. `src/hitl-service` and `apps/web`: reviewer work queue, evidence display, confirmation/correction/dismissal, and immutable audit actions.

## System boundaries

- **PostgreSQL** is the system of record for tenant data, inspections, event versions, and HITL actions. Enforce tenant isolation with Row Level Security.
- **Object storage** holds original media, ROI crops, and annotated evidence. Store references and integrity hashes in PostgreSQL; never put large media blobs in Kafka.
- **Kafka** is the durable workflow backbone. Topics are versioned and each consumer owns its own side effects.
- **Redis belongs at the API Gateway boundary** for rate limits, idempotency keys, and short-lived request state. Do not use Redis as a system of record.
- **Milvus** stores OSHA embeddings. Retrieval must also include lexical/BM25 matching and corpus version metadata.
- Providers such as GPT-4o and Gemini are untrusted external dependencies: set timeouts, bounded retries, cost limits, and fallback/HITL behavior.

## Data contracts and event rules

- Include `event_id`, `trace_id`, `tenant_id`, `inspection_id`, `schema_version`, and `occurred_at` in every Kafka event.
- Use normalized ROI coordinates in `[0, 1]`; retain original dimensions separately.
- Validate all untrusted input and all model output against explicit schemas before publishing or persisting it.
- Use an outbox pattern (or equivalent atomic handoff) between PostgreSQL writes and Kafka publishing.
- Consumers are idempotent by `event_id`; commit Kafka offsets only after durable side effects complete.
- Define retry limits and matching `*.dlq.v1` topics. A DLQ item must be observable and replayable.

## AI and retrieval rules

- Route only relevant ROIs to each specialist agent. Do not repeatedly send full media to every model.
- Specialist responses must include observation, ROI, visual rationale, confidence, and abstention reason when applicable.
- The synthesizer reconciles evidence; it must reject conflicts rather than averaging them into a result.
- The LLM-as-a-Judge is an evaluation signal, not the sole policy decision. The decision gate must enforce deterministic confidence/severity/HITL rules.
- The Evidence Renderer consumes only schema-validated decisions and coordinates. It uses deterministic image tooling (for example OpenCV or Pillow); no LLM draws annotations.
- Use RAG for current, citeable OSHA criteria. Do not fine-tune on regulatory text unless an ADR and offline evaluation demonstrate a clear need.
- Persist model name, provider, prompt version, retrieval corpus version, token counts, cost, latency, and output schema version with each decision.

## Security and privacy rules

- Authenticate every request and authorize every tenant-scoped read/write.
- Never log API keys, raw tokens, signed URLs, unredacted PII, or media bytes.
- Use signed object-storage URLs, encryption in transit and at rest, retention/deletion policies, and explicit face/vehicle-blurring decisions.
- Enforce media MIME sniffing, byte/pixel limits, decompression-bomb defense, content hashing, and malware scanning before processing.
- Keep Kafka, PostgreSQL, Redis, Milvus, and workers private; expose only the web application and API Gateway.

## Testing, evaluation, and release gates

- Write unit tests with implementation changes; add contract tests whenever schemas change.
- Add integration tests for the happy path and failures: duplicate event, provider timeout, worker crash/replay, DLQ, weak retrieval, conflicting evidence, and HITL routing.
- Maintain versioned golden data in `evals/` with no-violation cases, PPE, scaffolds, equipment proximity, occlusion, lighting, and adverse-weather scenarios.
- Evaluate per violation type: recall, precision, bounding-box IoU, citation groundedness, HITL overturn rate, P95 latency, and cost per inspection.
- Do not release a model, prompt, routing, or corpus change that regresses an agreed safety metric or exceeds latency/cost budgets.

## Tokenomics and observability

- Every job has `max_cost_usd` and `max_model_calls`; stop and route to HITL rather than silently exceeding its budget.
- Cache image hashes, embeddings, and retrieval results where policy permits.
- Emit structured telemetry with `trace_id`: status transitions, queue lag, model calls, tokens, cost, retries, ROI routing, retrieval scores, judge score, decision, and HITL outcome.
- Alert on DLQ growth, consumer lag, provider failures, latency/cost overruns, citation-quality degradation, elevated HITL overturns, and confidence drift.

## Working practices for agents

- Read this file and the relevant ADRs before changing code.
- Keep changes scoped to one bounded component. Do not modify another service's contract without updating `packages/contracts`, tests, documentation, and impacted consumers.
- Prefer small, reviewable commits. Do not commit generated dependencies, model weights, raw jobsite media, secrets, or local databases.
- Update an ADR when making a durable technology or architectural tradeoff.
- Update a runbook when adding a new operational failure mode or recovery action.
- Before concluding work, run the relevant formatter, tests, type checks, contract validation, and an end-to-end smoke test when the change crosses service boundaries.

## Definition of done

A change is done only when its contracts are versioned, tenant behavior is safe, failures are defined, observability is emitted, tests cover the intended behavior, and README/ADR/runbook updates are included where relevant.
