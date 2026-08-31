# QUALITY_MODEL

Status: CANONICAL

## Quality Objectives

The project quality model is a SearchLeads-specific reduction of ISO/IEC 25010 concepts focused on what actually constrains this repository.

## Characteristics

### Functional Suitability

- measures: precision, recall, false-merge rate, abstention rate, coverage of required fields
- target: conservative correctness over aggressive automation

### Reliability

- measures: replay success, recovery from interrupted migration, stable outputs over repeated runs
- target: failure is explicit and bounded

### Performance

- measures: latency, throughput, test runtime, persistence overhead
- target: adequate for local and batch processing, not premature optimization

### Security and Privacy

- measures: secret handling, access boundary clarity, evidence retention discipline
- target: no secret leakage, no implied authorization

### Maintainability

- measures: traceability density, test clarity, doc/code alignment, modular boundaries
- target: changes should not require rediscovering project rules

### Operability and Deployability

- measures: startup clarity, health/readiness definition, recovery procedures, deployment reproducibility
- target: operators can tell what is blocked and why, can restore canonical state from backup, can separate SEND_READY from system readiness, and can explain source authority/freshness for external facts

### Data Integrity

- measures: digest validation, envelope consistency, replay fidelity
- target: corrupted evidence is detected immediately

### Compliance and Authorization

- measures: policy versioning, manual approval boundaries, suppression precedence, send-ready proof completeness
- target: compliance decisions remain explicit, versioned, and fail closed

## Explicit Non-Goals

- maximizing recall at the expense of merge precision
- hiding uncertainty behind averages
- treating experimental benchmark results as production certification

## Evidence Rule

Local sanctioned benchmark evidence may establish a provisional operating policy when external challengers are partially blocked, but it does not by itself certify live production behavior.
