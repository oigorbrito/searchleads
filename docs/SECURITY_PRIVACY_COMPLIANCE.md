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
- engineering may prepare a legal-review packet and enforce the resulting policy, but it cannot self-approve the campaign legal basis
- manual campaign authorization remains a separate authority after compliance review

## Live Certification Requirements

- current repository evidence is insufficient to claim complete external certification
- any live certification must be documented as such and tied to evidence
- live certification artifacts must remain separate from internal regression evidence
- source authority is scoped per fact; certification of one fact does not authorize all facts from the same source
- freshness policy and revalidation due dates are mandatory for temporal facts
- an official consultation surface establishes source authority only for that surface; it does not establish a person-specific current status without a captured lookup

## Legal Source Facts

Observed against official sources on 2026-09-01:

- Presidencia da Republica / Planalto, Lei 13.709/2018 compiled text: https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709compilado.htm
- LGPD Art. 6 establishes principles including purpose, adequacy and necessity for personal-data processing
- LGPD Art. 7 lists legal bases and includes legitimate interest in item IX
- LGPD Art. 18 establishes data-subject rights against the controller
- ANPD legitimate-interest guidance: https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes/guia_orientativo_hipoteses_legais_tratamento_de_dados_pessoais_legitimo_interesse
- ANPD guidance requires contextual assessment and documentation around purpose, necessity/proportionality, safeguards and legitimate expectations
- engineering may implement safe defaults and collect review evidence, but it does not create legal approval

The canonical reviewer questions and authority ownership are defined in `EXTERNAL_GOVERNANCE_REVIEW_PACKET_V1.md` and `searchleads.external_governance`.

## External Source Authority Decisions

Observed on 2026-09-01:

- CFO publishes an official `Consulta de Profissionais` surface at https://website.cfo.org.br/busca-profissionais/
- this establishes the consultation source/surface, not the current registration status of any particular professional
- current professional status remains HUMAN_REVIEW and requires a person-specific captured lookup
- SERPRO lists an official `Consulta CNPJ - Servico Serpro (API)` service at https://www.serpro.gov.br/menu/suporte/css
- the official SERPRO API is distinct from the repository's historical `SERPRO transparency page` enrichment path
- the SERPRO transparency enrichment path is `NOT_REQUIRED` for the minimum commercial critical path; this is not a certification claim about the separate SERPRO API

## Unresolved Gates

- `LEGAL-001`: controller/compliance legal-basis and campaign review
- `EXT-BRASILAPI-001`: fresh source revalidation before campaign use
- `EXT-CFO-001`: person-specific current professional-registration verification when campaign policy depends on it
- `AUTH-CAMPAIGN-001`: campaign-specific manual authorization
- live contact deliverability remains separate from source publication and authorization

## Closed or Reclassified Gates

- SERPRO transparency enrichment path: removed from the minimum commercial critical path as `NOT_REQUIRED`
- suppression enforcement: internal fail-closed control remains mandatory and cannot be overridden by source certification
