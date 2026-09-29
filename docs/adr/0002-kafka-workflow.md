# ADR 0002: Kafka is the inspection workflow backbone

## Decision

Use Kafka for durable events between ingestion and workers.

## Rationale

Inspections are bursty and model calls are unreliable. Kafka permits replay, independent scaling, retry/DLQ handling, and audit-friendly progression.

## Consequences

Consumers must be idempotent, schemas versioned, and offsets committed only after durable side effects.
