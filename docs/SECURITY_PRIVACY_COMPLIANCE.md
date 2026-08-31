# SECURITY_PRIVACY_COMPLIANCE

Status: CANONICAL

## Data Handling

SearchLeads handles business contact data and associated evidence. That makes minimization, lineage, and access boundaries mandatory.

## Privacy and Minimization

- store only the evidence needed for the product purpose
- keep raw payloads only when they are required for replay and auditability
- avoid broad collection claims

## Contact Provenance

- every contact point must retain discovery evidence
- validation must be explicit and separate from discovery

## Security Assumptions

- external sources are untrusted until checked
- persisted records are trusted only within integrity constraints
- secrets never belong in canonical docs

## Access Boundaries

- runtime and repository access are separate concerns
- documentation does not authorize external action

## Campaign Compliance

- qualification is not send authorization
- SEND_READY requires a separate gate
- live commercial use requires legal/compliance evidence beyond product qualification

## Live Certification Requirements

- current repository evidence is insufficient to claim external certification
- any live certification must be documented as such and tied to evidence

## Unresolved Gates

- campaign legal review
- live contact deliverability
- send authorization
- jurisdiction-specific compliance sign-off

