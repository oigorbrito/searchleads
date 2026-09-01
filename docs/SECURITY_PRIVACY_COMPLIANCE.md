# SECURITY_PRIVACY_COMPLIANCE

Status: CANONICAL

## Data Handling

SearchLeads handles business contact data and associated evidence. That makes minimization, lineage, and access boundaries mandatory.

## Privacy and Minimization

- store only the evidence needed for the product purpose
- keep raw payloads only when they are required for replay and auditability
- avoid broad collection claims
- operational logs and telemetry should remain structured and redacted

## Contact Provenance

- every contact point must retain discovery evidence
- validation must be explicit and separate from discovery

## Security Assumptions

- external sources are untrusted until checked
- persisted records are trusted only within integrity constraints
- secrets never belong in canonical docs
- backup/restore must preserve integrity boundaries without exposing secrets

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
- live certification artifacts must remain separate from internal regression evidence
- source authority is scoped per fact; certification of one fact does not authorize all facts from the same source
- freshness policy and revalidation due dates are mandatory for temporal facts

## Legal Source Facts

- LGPD Art. 6 establishes purpose, adequacy, necessity, free access, and other principles for processing personal data
- LGPD Art. 7 lists legal bases including consent and legitimate interest
- LGPD Art. 18 and ANPD guidance preserve data-subject rights to information, access, correction, blocking, deletion, revocation, and opposition where applicable
- ANPD legitimate-interest guidance frames a balancing test with purpose, necessity, and safeguards
- engineering may implement safe defaults and require review, but it does not create legal approval

## Unresolved Gates

- campaign legal review
- live contact deliverability
- send authorization
- jurisdiction-specific compliance sign-off
- human verification for professional registration remains external
- legal sign-off remains external unless a formal policy owner records approval
