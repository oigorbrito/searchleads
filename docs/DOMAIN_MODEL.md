# DOMAIN_MODEL

Status: CANONICAL

## Concepts

### Company

- meaning: a business entity that can own evidence-backed observations.
- identity: `company_id`
- ownership: owns company-scoped evidence and derived records
- lifecycle: discovered, normalized, resolved, enriched, exported
- references: candidate facts, canonical facts, people, contact points, leads
- invariants: non-blank identity; no implicit merge authority

### PersonIdentity

- meaning: stable person identity independent from company relationship scope.
- identity: `person_id`
- ownership: owns person-scoped observation history
- lifecycle: observed, triaged, matched, reviewed, merged if authorized
- references: relationship evidence, contact points, role observations
- invariants: identity must not collapse into company membership

### PersonCompanyRelationship

- meaning: scoped relationship between a person and a company.
- identity: relationship identifier, or compound identity if implemented that way
- ownership: owns role/contact observations that depend on the company context
- lifecycle: discovered, assessed, reviewed, resolved
- references: evidence, person identity, company identity
- invariants: one person may have multiple relationships

### ProfessionalRegistration

- meaning: registration or credential linked to a person and often relevant to a relationship.
- identity: registration identifier
- ownership: person-scoped, with relationship applicability where needed
- lifecycle: observed, validated, expiring, stale
- references: evidence, issuer, role context
- invariants: must not be implied from role text alone

### ContactPoint

- meaning: discovered contact method such as email, phone, WhatsApp, profile, or form.
- identity: `contact_id`
- ownership: owner scope is explicit
- lifecycle: discovered, validated, stale, invalid
- references: discovery evidence and optional validation evidence
- invariants: discovered state cannot carry validation metadata

### RelationshipContactLink

- meaning: link between a contact point and a person-company relationship.
- identity: link identifier or compound link identity
- ownership: relationship-scoped
- lifecycle: linked, validated, revoked
- references: contact point, relationship, evidence
- invariants: link scope must be explicit

### Evidence

- meaning: raw observed artifact with integrity metadata.
- identity: `evidence_id`
- ownership: source-backed and persistently retained
- lifecycle: captured, stored, replayed, invalidated by integrity failure only
- references: source, payload, timestamps, metadata
- invariants: replayable and digest-protected

### Statement

- meaning: derived or normalized assertion produced from evidence.
- identity: statement identifier
- ownership: derived, not raw
- lifecycle: created, revised, superseded, conflicted
- references: evidence links, provenance, subject
- invariants: must remain distinguishable from Evidence

### StatementEvidenceLink

- meaning: many-to-many bridge between statements and evidence.
- identity: compound link
- ownership: statement-data layer
- lifecycle: created with statement, updated only through controlled migrations
- references: Statement, Evidence
- invariants: links must be reconstructible

### Lead

- meaning: commercial wrapper around a company or person-centered qualification target.
- identity: `lead_id`
- ownership: commercial pipeline
- lifecycle: candidate, review, qualified, disqualified
- references: qualification decision, company/person context
- invariants: lead status must match qualification state

### QualificationDecision

- meaning: explicit decision over commercial qualification status.
- identity: decision identifier
- ownership: qualification policy
- lifecycle: created, reviewed, superseded
- references: policy ID, evidence, lead target
- invariants: policy mismatch is invalid
