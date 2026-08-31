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

The product exposes discovery, validation, qualification, export, acceptance, and operational API capabilities. It does not promise broad crawling, silent fuzzy identity merge, or campaign authorization.

### Domain View

Canonical domain centers on Company, Person, ContactPoint, Evidence, statement/fact concepts, and Lead wrappers. Relationship scope is explicit.

### Evidence/Data View

Raw Evidence is persisted separately from derived records. Storage integrity is checked with digests and replay semantics.

### Entity Resolution View

Company ER and Person ER are conservatively provisioned from local benchmark evidence. Review and abstention are first-class outcomes, and external challenger breadth remains open.

### Acquisition View

Acquisition is an adapter boundary, not the root chassis. The current repository includes a local fallback runtime adapter and a thin operational chassis. Crawlee remains optional breadth, not the baseline authority.

### Application/API View

A thin application layer composes the canonical domain, persistence, qualification/review/export surfaces, and acquisition/runtime adapters. The current chassis exposes health, readiness, acquisition, evidence, qualification, review, export, and capabilities endpoints or equivalent local call points.

### Deployment View

Single-process local development and test execution are supported now. A lightweight operational chassis runs without Crawlee. Deployment topology is documented separately and remains constrained by current evidence.

### Operations View

A dedicated operational layer handles startup, shutdown, health, readiness, backup, restore, recovery, structured events, SEND_READY evaluation, source authority mapping, and compliance proof bundles. These concerns are separate from the canonical domain and separate again from live certification.

### Compliance View

Qualification is not send readiness. Contact provenance, campaign legality, source authority, and live certification remain separate gates.

## Component Boundaries

- domain model
- persistence layer
- evidence/provenance layer
- entity resolution
- discovery/validation/qualification workflows
- application/API surface
- acquisition/runtime adapters
- review/export/lead-materialization adapters
- operational lifecycle, telemetry, and certification helpers
- authority/freshness/compliance proof helpers

## Trust Boundaries

- external web sources
- persisted raw evidence
- derived statements and facts
- manual review decisions
- live certification and compliance gates
- source authority and freshness maps

## Unresolved Issues

- Company ER is provisionally benchmark-closed on the local sanctioned runtime, but external challenger breadth remains open.
- Person ER is provisionally benchmark-closed on the local sanctioned runtime, but external challenger breadth remains open.
- Crawlee breadth remains optional and not yet operationally proven in this repository.
- deployment topology is now explicit for the local single-process path, but live certification and compliance remain separate external gates.
- live certification, source authority freshness, and compliance policy remain separate external gates.
