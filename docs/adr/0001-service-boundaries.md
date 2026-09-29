# ADR 0001: Service boundaries follow durable workflow responsibilities

## Decision

Use independently deployable services for gateway, ingestion, each AI processing stage, decisioning, rendering, and HITL. Shared code is limited to contracts and dependency-light primitives.

## Rationale

The stages have distinct scaling, security, failure, and ownership needs. This prevents model-provider failures or rendering load from blocking secure ingestion.

## Consequences

Cross-service communication requires versioned contracts, correlation IDs, observability, and integration tests.
