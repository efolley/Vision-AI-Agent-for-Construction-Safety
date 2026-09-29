# ADR 0003: PostgreSQL is the system of record

## Decision

Use PostgreSQL for tenant data, inspection state, event versions, reviewer actions, and the transactional outbox.

## Rationale

The platform needs relational integrity, consistent state transitions, strong auditability, and tenant-scoped Row Level Security.

## Consequences

Large media remains in object storage; PostgreSQL stores references, hashes, and metadata.
