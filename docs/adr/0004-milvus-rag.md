# ADR 0004: Milvus supports evidence-grounded OSHA retrieval

## Decision

Use hybrid lexical/BM25 and Milvus vector retrieval over a versioned OSHA corpus.

## Rationale

The system must produce inspectable, current citations. Hybrid retrieval improves exact regulatory matching while semantic search handles varied visual descriptions.

## Consequences

Every result records corpus version, retrieved passages, scores, and selected citation. Retrieval does not itself establish a violation.
