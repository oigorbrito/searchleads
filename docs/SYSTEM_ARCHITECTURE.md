# SYSTEM_ARCHITECTURE

Status: CANONICAL
Method: architecture description aligned to ISO/IEC/IEEE 42010 concepts.

## System Context

SearchLeads is a lead discovery and qualification system that consumes external evidence, derives domain facts, persists raw evidence, and produces conservative commercial outputs.

## Stakeholders

- product owner
- engineering
- operations
- compliance reviewers
- external integration maintainers
- future automation agents

## Concerns

- identity correctness
- evidence integrity
- deterministic replay
- conservative entity resolution
- operability and recovery
- release readiness
- compliance separation

## Architectural Drivers

- preserve raw evidence
- make review/abstention explicit
- keep commercial qualification separate from send readiness
- support measured quality gates
- minimize hidden coupling

## Viewpoints

### Product View

The product exposes discovery, validation, qualification, export, and acceptance capabilities. It does not promise broad crawling, silent fuzzy identity merge, or campaign authorization.

### Domain View

Canonical domain centers on Company, Person, ContactPoint, Evidence, statement/fact concepts, and Lead wrappers. Relationship scope is explicit.

### Evidence/Data View

Raw Evidence is persisted separately from derived records. Storage integrity is checked with digests and replay semantics.

### Entity Resolution View

Company ER and Person ER remain conservative and benchmark-dependent. Review and abstention are first-class outcomes.

### Acquisition View

Acquisition is an adapter boundary, not the root chassis. Existing runtime experiments remain evidence, not authority.

### Application/API View

A thin application layer should compose the canonical domain, persistence, and acquisition/runtime adapters.

### Deployment View

Single-process local development and test execution are supported now. Operational deployment topology is documented separately and remains constrained by current evidence.

### Compliance View

Qualification is not send readiness. Contact provenance, campaign legality, and live certification remain separate gates.

## Component Boundaries

- domain model
- persistence layer
- evidence/provenance layer
- entity resolution
- discovery/validation/qualification workflows
- application/API surface
- acquisition/runtime adapters

## Trust Boundaries

- external web sources
- persisted raw evidence
- derived statements and facts
- manual review decisions
- live certification and compliance gates

## Unresolved Issues

- Company ER winner is not yet benchmark-closed.
- Person ER winner is not yet benchmark-closed.
- deployment topology remains lightly specified compared with implementation depth.

