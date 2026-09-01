# EXTERNAL_GOVERNANCE_REVIEW_PACKET_V1

Status: CANONICAL REVIEW INPUT
Observed: 2026-09-01
Branch: `work/chassis-implementation-v1`

## Purpose

Reduce the remaining external/human/legal critical path to explicit authority decisions without converting engineering research into legal approval, person-specific professional-registration certification, or campaign authorization.

## Authority sources observed

### LGPD — official compiled law

Publisher: Presidencia da Republica / Planalto
Locator: https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709compilado.htm

Observed facts used by this packet:
- Art. 6 requires processing to observe principles including purpose, adequacy and necessity.
- Art. 7 lists legal bases for personal-data processing and includes legitimate interest in item IX.
- Art. 18 establishes rights that a data subject may exercise against the controller.

Engineering conclusion: these provisions identify compliance inputs and fail-closed requirements. They do not by themselves approve the SearchLeads campaign.

### ANPD — legitimate-interest guidance

Publisher: Autoridade Nacional de Protecao de Dados
Locator: https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes/guia_orientativo_hipoteses_legais_tratamento_de_dados_pessoais_legitimo_interesse

Observed facts used by this packet:
- ANPD publishes an official guidance document specifically for legitimate-interest processing.
- The guidance frames analysis around a concrete purpose, necessity/proportionality, safeguards and the data subject's legitimate expectations.
- Documentation of the analysis supports accountability and review.

Engineering conclusion: SearchLeads can prepare the evidence packet and enforcement controls, but a controller/compliance reviewer must select and approve the legal basis for the exact campaign.

### CFO — professional consultation surface

Publisher: Conselho Federal de Odontologia
Locator: https://website.cfo.org.br/busca-profissionais/

Observed fact used by this packet:
- CFO publishes an official public surface named `Consulta de Profissionais` and directs users to its consultation system.

Engineering conclusion: source authority for the consultation surface is established. Current status for a particular professional is not established until a person-specific lookup is performed and captured with timestamp/evidence.

### SERPRO — Consulta CNPJ service

Publisher: Servico Federal de Processamento de Dados — SERPRO
Locator: https://www.serpro.gov.br/menu/suporte/css

Observed facts used by this packet:
- SERPRO lists `Consulta CNPJ - Servico Serpro (API)` as a service.
- SERPRO documentation describes its API products as separately contracted/authenticated services; production use is distinct from a public transparency-page capture.

Engineering conclusion: the existence of the official SERPRO CNPJ API does not make the existing SearchLeads `SERPRO transparency page` enrichment path mandatory. The minimum commercial path already uses the separate BrasilAPI CNPJ source and does not require the SERPRO transparency page to reach an engineering RC or a legal-review packet.

## Critical-path decision

The canonical external-governance gate set for the minimum bounded dental pilot is:

1. `EXT-BRASILAPI-001` — REVIEW_REQUIRED: fresh product-source certification/revalidation remains required before use.
2. `EXT-SERPRO-001` — NOT_REQUIRED: the SERPRO transparency enrichment path is removed from the minimum commercial critical path. This does not certify or reject SERPRO's official Consulta CNPJ API as a future alternative source.
3. `EXT-CFO-001` — REVIEW_REQUIRED: person-specific current professional-registration evidence is required when campaign policy depends on professional status.
4. `LEGAL-001` — REVIEW_REQUIRED: controller/compliance legal-basis decision and campaign-specific balancing/necessity/safeguards review remain external.
5. `AUTH-CAMPAIGN-001` — BLOCKED: campaign-specific manual authorization remains absent.

## LEGAL-001 review questions

The designated reviewer must record an explicit answer for the exact campaign policy version:

- Which LGPD legal basis is approved for this campaign purpose, contact class and channel?
- If legitimate interest is relied upon, is the controller's documented purpose, necessity and balancing analysis sufficient?
- What notice, opposition, suppression and opt-out controls are required before first contact?
- What retention/deletion period is approved for contact data and raw Evidence?
- Are any source classes, contact classes or uses of professional-registration data prohibited or review-only?

No default answer is implied by this document.

## Human professional-registration verification packet

For each professional whose current CFO/CRO status is campaign-critical, capture at minimum:

- canonical `PersonIdentity` ID;
- professional name/identifier used in the consultation;
- CFO/CRO source/surface identifier;
- lookup timestamp;
- observed status exactly as displayed;
- raw Evidence or replay-safe capture;
- integrity digest;
- reviewer identity;
- decision and reason code;
- revalidation/expiry rule.

Absence of an end date, missing data, or a successful page load must never be converted into `VERIFIED_ACTIVE`.

## Campaign authorization boundary

Even after `LEGAL-001` and `EXT-CFO-001` are satisfied, SearchLeads must remain non-sending until a campaign-owner/manual authorization record references:

- the approved compliance-policy version;
- the bounded audience/campaign definition;
- the approved channel/contact class;
- the approval timestamp and authorizer identity;
- any expiration/revocation condition.

Suppression always wins. Revocation or expiry invalidates the authorization.

## Non-claims

This packet does not claim:
- legal advice or legal approval;
- live deliverability;
- permission to contact any person;
- current CFO/CRO registration for any named individual;
- campaign authorization;
- that BrasilAPI is an official government authority;
- that SERPRO is required for the current minimum product path.
