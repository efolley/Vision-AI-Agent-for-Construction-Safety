# ADR 0005: Use provider adapters and scoped model roles

## Decision

Use provider adapters: GPT-4o for scene/synthesis/judging and Gemini Flash for cost-efficient specialist analysis. Calls are bounded by time, retries, and job cost limits.

## Rationale

Different stages have different reasoning and cost needs. Provider adapters permit measured changes without leaking provider-specific APIs across the platform.

## Consequences

Provider calls require versioned prompts, schema validation, token/cost telemetry, fallback/HITL policy, and offline regression evaluation before release.
